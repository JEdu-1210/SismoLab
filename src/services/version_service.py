from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from src.models.Returnings import (
    BaseReturn,
    DataAndMsgReturn
)

from src.services.persistencia import (
    PersistenceService
)

from src.services.undo_service import (
    UndoService
)

from src.utils.Files import FilesUtils


class VersionService:

    VERSION_SCHEMA = (
        "SismoLabAVLVersion"
    )

    VERSION_SCHEMA_VERSION = 1


    def __init__(
        self,
        storage_dir="Data/versions"
    ):

        self.storage_dir = Path(
            storage_dir
        )


        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        self.undo_service = (
            UndoService()
        )


    # =========================================================
    # VALIDAR NOMBRE
    # =========================================================

    def _normalize_name(
        self,
        name
    ):

        if not isinstance(
            name,
            str
        ):

            raise ValueError(
                "Version name must "
                "be a string"
            )


        name = name.strip()


        if name == "":

            raise ValueError(
                "Version name "
                "cannot be empty"
            )


        return name


    # =========================================================
    # ARCHIVO DE UNA VERSIÃ“N
    # =========================================================

    # El hash evita colisiones entre nombres
    # parecidos al convertirlos a archivo.
    def _get_filepath(
        self,
        version_name
    ):

        version_name = (
            self._normalize_name(
                version_name
            )
        )


        safe_part = "".join(

            char

            if (
                char.isalnum()
                or
                char in (
                    "_",
                    "-"
                )
            )

            else "_"

            for char
            in version_name
        )


        safe_part = (
            safe_part[:40]
            or
            "version"
        )


        digest = (
            sha256(
                version_name
                .encode(
                    "utf-8"
                )
            )
            .hexdigest()[:10]
        )


        return (
            self.storage_dir
            /
            f"{safe_part}_{digest}.json"
        )


    # =========================================================
    # CREAR VERSIÃ“N
    # =========================================================

    def create_version(
        self,
        name,
        description,
        sismolab,
        overwrite=False
    ):

        response = DataAndMsgReturn()


        try:

            name = (
                self._normalize_name(
                    name
                )
            )


        except ValueError as exc:

            response.ok = False
            response.error = str(exc)

            return response


        if description is None:

            description = ""


        if not isinstance(
            description,
            str
        ):

            response.ok = False

            response.error = (
                "Version description "
                "must be a string"
            )

            return response


        filepath = (
            self._get_filepath(
                name
            )
        )


        if (
            filepath.is_file()
            and
            not overwrite
        ):

            response.ok = False

            response.error = (
                f"Version '{name}' "
                "already exists"
            )

            return response


        state = (
            PersistenceService
            .export_state(
                sismolab
            )
        )


        version_data = {

            "schema":
                self.VERSION_SCHEMA,

            "schema_version":
                self.VERSION_SCHEMA_VERSION,

            "name":
                name,

            "description":
                description.strip(),

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(
                    timespec="seconds"
                ),

            # IMPORTANTE:
            #
            # Este state NO contiene:
            # - undo stack
            # - otras versiones
            #
            # justamente como exige
            # el proyecto.
            "state":
                state
        }


        save_result = (
            FilesUtils.write_json(
                str(filepath),
                version_data
            )
        )


        if not save_result.ok:

            response.ok = False

            response.error = (
                "Could not save version: "
                f"{save_result.error}"
            )

            return response


        response.data = {

            "name":
                name,

            "description":
                description.strip(),

            "filepath":
                str(filepath),

            "created_at":
                version_data[
                    "created_at"
                ]
        }


        response.msg = (
            f"Version '{name}' "
            "saved successfully"
        )


        return response


    # =========================================================
    # LISTAR VERSIONES
    # =========================================================

    def list_versions(
        self
    ):

        response = DataAndMsgReturn()

        versions = []


        try:

            for filepath in (
                self.storage_dir
                .glob("*.json")
            ):

                read_result = (
                    FilesUtils.read_json(
                        str(filepath)
                    )
                )


                if (
                    not read_result.ok
                    or
                    not isinstance(
                        read_result.data,
                        dict
                    )
                ):

                    continue


                data = read_result.data


                if (
                    data.get("schema")
                    !=
                    self.VERSION_SCHEMA
                ):

                    continue


                if (
                    data.get(
                        "schema_version"
                    )
                    !=
                    self.VERSION_SCHEMA_VERSION
                ):

                    continue


                versions.append({

                    "name":
                        data.get(
                            "name"
                        ),

                    "description":
                        data.get(
                            "description",
                            ""
                        ),

                    "created_at":
                        data.get(
                            "created_at"
                        ),

                    "filename":
                        filepath.name
                })


            versions.sort(
                key=lambda item:
                    item.get(
                        "created_at",
                        ""
                    ),
                reverse=True
            )


            response.data = {

                "versions":
                    versions,

                "count":
                    len(versions)
            }


            response.msg = (
                f"{len(versions)} "
                "persistent version(s) found"
            )


            return response


        except Exception as exc:

            response.ok = False
            response.error = str(exc)

            return response


    # =========================================================
    # RESTAURAR VERSIÃ“N
    # =========================================================

    def restore_version(
        self,
        name,
        sismolab
    ):

        response = DataAndMsgReturn()


        try:

            name = (
                self._normalize_name(
                    name
                )
            )


        except ValueError as exc:

            response.ok = False
            response.error = str(exc)

            return response


        filepath = (
            self._get_filepath(
                name
            )
        )


        if not filepath.is_file():

            response.ok = False

            response.error = (
                f"Version '{name}' "
                "does not exist"
            )

            return response


        read_result = (
            FilesUtils.read_json(
                str(filepath)
            )
        )


        if (
            not read_result.ok
            or
            not isinstance(
                read_result.data,
                dict
            )
        ):

            response.ok = False

            response.error = (
                read_result.error
                or
                "Could not read version"
            )

            return response


        version_data = (
            read_result.data
        )


        if (
            version_data.get(
                "schema"
            )
            !=
            self.VERSION_SCHEMA
        ):

            response.ok = False

            response.error = (
                "Invalid version schema"
            )

            return response


        if (
            version_data.get(
                "schema_version"
            )
            !=
            self.VERSION_SCHEMA_VERSION
        ):

            response.ok = False

            response.error = (
                "Unsupported version "
                "schema version"
            )

            return response


        state = (
            version_data.get(
                "state"
            )
        )


        if not isinstance(
            state,
            dict
        ):

            response.ok = False

            response.error = (
                "Version does not contain "
                "a valid state"
            )

            return response


        # Guardamos el estado ANTERIOR
        # para poder deshacer esta restauraciÃ³n.
        state_before = (
            self.undo_service
            .capture_state(
                sismolab
            )
        )


        restore_result = (
            PersistenceService
            .apply_state(
                sismolab,
                state,
                success_message=(
                    f"Version '{name}' "
                    "restored successfully"
                )
            )
        )


        if not restore_result.ok:

            response.ok = False
            response.error = (
                restore_result.error
            )

            return response


        # La restauraciÃ³n sÃ­ ocurriÃ³.
        # Ahora registramos UNA sola acciÃ³n.
        self.undo_service.push_snapshot(
            sismolab,
            "RESTORE_VERSION",
            (
                "Restore persistent version "
                f"'{name}'"
            ),
            state_before
        )


        response.data = {

            "name":
                version_data.get(
                    "name"
                ),

            "description":
                version_data.get(
                    "description",
                    ""
                ),

            "created_at":
                version_data.get(
                    "created_at"
                )
        }


        response.msg = (
            f"Version '{name}' "
            "restored successfully"
        )


        return response


    # =========================================================
    # ELIMINAR UNA VERSIÃ“N
    #
    # No es una operaciÃ³n del escenario,
    # por eso no entra en Undo operativo.
    # =========================================================

    def delete_version(
        self,
        name
    ):

        response = BaseReturn()


        try:

            filepath = (
                self._get_filepath(
                    name
                )
            )


            if not filepath.is_file():

                response.ok = False

                response.error = (
                    f"Version '{name}' "
                    "does not exist"
                )

                return response


            filepath.unlink()


            return response


        except Exception as exc:

            response.ok = False
            response.error = str(exc)

            return response
