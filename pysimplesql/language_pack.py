""" ChatGPT prompt:
I'm working on language localization for my python application.
Can you look at this dict and make a spanish version?
Please keep strings in brackets {} unaltered.
Please keep double spaces and extra spaces unaltered.
Please keep \n line breaks unaltered. {dict here}
"""

lp_template = {
    "button_cancel": " Cancel ",
    "button_ok": "  OK  ",
    "button_yes": " Yes ",
    "button_no": "  No  ",
    "info_popup_title": "Info",
    # Form save_records
    # ------------------------
    "form_save_partial": "Some updates were saved successfully;",
    "form_save_problem": "There was a problem saving updates to the following tables:\n{tables}.",
    "form_save_success": "Updates saved successfully.",
    "form_save_none": "There were no updates to save.",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "There were no updates to save.",
    "dataset_save_none": "There were no changes to save!",
    "dataset_save_success": "Updates saved successfully.",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Unsaved Changes",
    "form_prompt_save": "You have unsaved changes!\nWould you like to save them first?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Unsaved Changes",
    "dataset_prompt_save": "You have unsaved changes!\nWould you like to save them first?",
    # DataSet save_record
    "dataset_save_callback_false_title": "Callback Prevented Save",
    "dataset_save_callback_false": "Updates not saved.",
    "dataset_save_keyed_fail_title": "Problem Saving",
    "dataset_save_keyed_fail": "Query failed: {exception}.",
    "dataset_save_fail_title": "Problem Saving",
    "dataset_save_fail": "Query failed: {exception}.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Confirm Deletion",
    "delete_cascade": "Are you sure you want to delete this record?\nKeep in mind that child records:\n({children})\nwill also be deleted!",
    "delete_single": "Are you sure you want to delete this record?",
    # Failed Ok Popup
    "delete_failed_title": "Problem Deleting",
    "delete_failed": "Query failed: {exception}.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record has children
    "duplicate_child_title": "Confirm Duplication",
    "duplicate_child": "This record has child records:\n(in {children})\nWhich records would you like to duplicate?",
    "duplicate_child_button_dupparent": "Only duplicate this record.",
    "duplicate_child_button_dupboth": "Duplicate this record and its children.",
    # Popup when record is single
    "duplicate_single_title": "Confirm Duplication",
    "duplicate_single": "Are you sure you want to duplicate this record?",
    # Failed Ok Popup
    "duplicate_failed_title": "Problem Duplicating",
    "duplicate_failed": "Query failed: {exception}.",
    # Quick Editor
    "quick_edit_title": "Quick Edit - {data_key}",
}

lp_yoda = {
    "button_cancel": " Cancel, you will ",
    "button_ok": " OK, you must ",
    "button_yes": " Yes, use the Force ",
    "button_no": " No, use the Force not ",
    "info_popup_title": "Info, I have",
    # Form save_records
    # ------------------------
    "form_save_partial": "Some updates, saved successfully they were;",
    "form_save_problem": "There was a problem, saving updates to the following tables:\n{tables}.",
    "form_save_success": "Updates, saved successfully they were.",
    "form_save_none": "There were no updates, to save.",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "There were no updates, to save.",
    "dataset_save_none": "There were no changes, to save!",
    "dataset_save_success": "Updates, saved successfully they were.",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Unsaved Changes, you have",
    "form_prompt_save": "Unsaved changes, you have!\nWould you like to save them, first would you?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Unsaved Changes, you have",
    "dataset_prompt_save": "Unsaved changes, you have!\nWould you like to save them, first would you?",
    # DataSet save_record
    "dataset_save_callback_false_title": "Callback Prevented Save, it did",
    "dataset_save_callback_false": "Updates, not saved they were.",
    "dataset_save_keyed_fail_title": "Problem Saving, there is",
    "dataset_save_keyed_fail": "Query failed, {exception} did.",
    "dataset_save_fail_title": "Problem Saving, there is",
    "dataset_save_fail": "Query failed, {exception} did.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Confirm Deletion, you must",
    "delete_cascade": "Are you sure you want to delete, this record you do?\nKeep in mind that child records, you will also delete:\n({children})\n",
    "delete_single": "Are you sure you want to delete, this record you do?",
    # Failed Ok Popup
    "delete_failed_title": "Problem Deleting, there is",
    "delete_failed": "Query failed, {exception} did.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record has children
    "duplicate_child_title": "Confirm Duplication, you must",
    "duplicate_child": "This record, has child records, it does:\n(in {children})\nWhich records, would you like to duplicate, hmmm?",
    "duplicate_child_button_dupparent": "Only duplicate, this record you will.",
    "duplicate_child_button_dupboth": "Duplicate, this record and its children, you will.",
    # Popup when record is single
    "duplicate_single_title": "Confirm Duplication, you must",
    "duplicate_single": "Are you sure you want to duplicate, this record you do?",
    # Failed Ok Popup
    "duplicate_failed_title": "Problem Duplicating, there is",
    "duplicate_failed": "Query failed, {exception} did.",
    "quick_edit_title": "Quick Edit, {data_key} - you will",
}

lp_es = {
    "button_cancel": " Cancelar ",
    "button_ok": " Aceptar ",
    "button_yes": " Sí ",
    "button_no": " No ",
    "info_popup_title": "Información",
    # Form save_records
    # ------------------------
    "form_save_partial": "Algunas actualizaciones se guardaron con éxito;",
    "form_save_problem": "Hubo un problema al guardar actualizaciones en las siguientes tablas:\n{tables}.",
    "form_save_success": "Actualizaciones guardadas con éxito.",
    "form_save_none": "No había actualizaciones que guardar.",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "No había actualizaciones que guardar.",
    "dataset_save_none": "¡No hay cambios que guardar!",
    "dataset_save_success": "Actualizaciones guardadas con éxito.",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Cambios no guardados",
    "form_prompt_save": "¡Tiene cambios sin guardar!\n¿Desea guardarlos primero?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Cambios no guardados",
    "dataset_prompt_save": "¡Tiene cambios sin guardar!\n¿Desea guardarlos primero?",
    # DataSet save_record
    "dataset_save_callback_false_title": "La llamada de retorno impidió guardar",
    "dataset_save_callback_false": "Actualizaciones no guardadas.",
    "dataset_save_keyed_fail_title": "Problema al guardar",
    "dataset_save_keyed_fail": "Falló la consulta: {exception}.",
    "dataset_save_fail_title": "Problema al guardar",
    "dataset_save_fail": "Falló la consulta: {exception}.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Confirmar Eliminación",
    "delete_cascade": "¿Está seguro de que desea eliminar este registro?\nRecuerde que los registros secundarios:\n({children})\n¡También se eliminarán!",
    "delete_single": "¿Está seguro de que desea eliminar este registro?",
    # Failed Ok Popup
    "delete_failed_title": "Problema al eliminar",
    "delete_failed": "Falló la consulta: {exception}.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record has children
    "duplicate_child_title": "Confirmar Duplicación",
    "duplicate_child": "Este registro tiene registros secundarios:\n(en {children})\n¿Qué registros desea duplicar?",
    "duplicate_child_button_dupparent": "Duplicar solo este registro.",
    "duplicate_child_button_dupboth": "Duplicar este registro y sus registros secundarios.",
    # Popup when record is single
    "duplicate_single_title": "Confirmar Duplicación",
    "duplicate_single": "¿Está seguro de que desea duplicar este registro?",
    # Failed Ok Popup
    "duplicate_failed_title": "Problema al duplicar",
    "duplicate_failed": "Falló la consulta: {exception}.",
    "quick_edit_title": "Edición Rápida - {data_key}",
}
