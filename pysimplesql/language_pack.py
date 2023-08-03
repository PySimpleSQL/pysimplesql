r"""ChatGPT prompt:
I'm working on language localization for my python application.
Can you look at this dict and make a spanish version?
Please keep strings in brackets {} unaltered.
Please keep double spaces and extra spaces unaltered.
Please keep \n line breaks unaltered.

Note: You may need to split lp_template into two dicts if ChatGPT stalls at the end.

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
"""

lp_90s = {
    "button_cancel": " Cancel ",
    "button_ok": " OK ",
    "button_yes": " Yes ",
    "button_no": " No ",
    "info_popup_title": "Info, like totally",
    # Form save_records
    # ------------------------
    "form_save_partial": "Some updates were saved successfully, yo;",
    "form_save_problem": "Whoa, there was a gnarly problem saving updates to the following tables:\n{tables}.",
    "form_save_success": "Updates saved successfully, dude!",
    "form_save_none": "Whoa, there were no updates to save, bummer.",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "Sorry, bro, there were no updates to save.",
    "dataset_save_none": "Bummer, there were no changes to save, man!",
    "dataset_save_success": "Updates saved successfully, rad!",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Unsaved Changes, dude",
    "form_prompt_save": "Hey, dude, you've got some gnarly unsaved changes!\nWould you like to save them first or what?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Unsaved Changes, man",
    "dataset_prompt_save": "Hey, man, you've got some gnarly unsaved changes!\nWould you like to save them first or what?",
    # DataSet save_record
    "dataset_save_callback_false_title": "Callback Prevented Save, dude",
    "dataset_save_callback_false": "Nah, bro, updates not saved.",
    "dataset_save_keyed_fail_title": "Problem Saving, man",
    "dataset_save_keyed_fail": "Bummer, query failed: {exception}.",
    "dataset_save_fail_title": "Problem Saving, dude",
    "dataset_save_fail": "Dude, query failed: {exception}.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Confirm Deletion, man",
    "delete_cascade": "Whoa, are you sure you want to delete this record?\nKeep in mind that child records:\n({children})\nwill also be deleted!",
    "delete_single": "Hey, dude, are you sure you want to delete this record?",
    # Failed Ok Popup
    "delete_failed_title": "Problem Deleting, man",
    "delete_failed": "Bummer, query failed: {exception}.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record has children
    "duplicate_child_title": "Confirm Duplication, dude",
    "duplicate_child": "This record has child records:\n(in {children})\nWhich records would you like to duplicate?",
    "duplicate_child_button_dupparent": "Only duplicate this record, dude.",
    "duplicate_child_button_dupboth": "Duplicate this record and its children, totally awesome!",
    # Popup when record is single
    "duplicate_single_title": "Confirm Duplication, bro",
    "duplicate_single": "Hey, bro, are you sure you want to duplicate this record?",
    # Failed Ok Popup
    "duplicate_failed_title": "Problem Duplicating, dude",
    "duplicate_failed": "Whoa, query failed: {exception}.",
    # Quick Editor
    "quick_edit_title": "Quick Edit - {data_key}, yo",
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

lp_de = {
    "button_cancel": " Abbrechen ",
    "button_ok": " OK ",
    "button_yes": " Ja ",
    "button_no": " Nein ",
    "info_popup_title": "Info",
    # Form save_records
    # ------------------------
    "form_save_partial": "Einige Aktualisierungen wurden erfolgreich gespeichert;",
    "form_save_problem": "Beim Speichern der Aktualisierungen in folgenden Tabellen ist ein Problem aufgetreten:\n{tables}.",
    "form_save_success": "Aktualisierungen erfolgreich gespeichert.",
    "form_save_none": "Es gab keine Aktualisierungen zum Speichern.",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "Es gab keine Aktualisierungen zum Speichern.",
    "dataset_save_none": "Es gab keine Änderungen zum Speichern!",
    "dataset_save_success": "Aktualisierungen erfolgreich gespeichert.",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Ungespeicherte Änderungen",
    "form_prompt_save": "Sie haben ungespeicherte Änderungen!\nMöchten Sie diese zuerst speichern?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Ungespeicherte Änderungen",
    "dataset_prompt_save": "Sie haben ungespeicherte Änderungen!\nMöchten Sie diese zuerst speichern?",
    # DataSet save_record
    "dataset_save_callback_false_title": "Rückruf hat Speichern verhindert",
    "dataset_save_callback_false": "Aktualisierungen wurden nicht gespeichert.",
    "dataset_save_keyed_fail_title": "Fehler beim Speichern",
    "dataset_save_keyed_fail": "Abfrage fehlgeschlagen: {exception}.",
    "dataset_save_fail_title": "Fehler beim Speichern",
    "dataset_save_fail": "Abfrage fehlgeschlagen: {exception}.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Löschen bestätigen",
    "delete_cascade": "Sind Sie sicher, dass Sie diesen Datensatz löschen möchten?\nBeachten Sie, dass untergeordnete Datensätze:\n({children})\nauch gelöscht werden!",
    "delete_single": "Sind Sie sicher, dass Sie diesen Datensatz löschen möchten?",
    # Failed Ok Popup
    "delete_failed_title": "Problem beim Löschen",
    "delete_failed": "Abfrage fehlgeschlagen: {exception}.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record has children
    "duplicate_child_title": "Duplikation bestätigen",
    "duplicate_child": "Dieser Datensatz hat untergeordnete Datensätze:\n(in {children})\nWelche Datensätze möchten Sie duplizieren?",
    "duplicate_child_button_dupparent": "Nur diesen Datensatz duplizieren.",
    "duplicate_child_button_dupboth": "Diesen Datensatz und seine untergeordneten Datensätze duplizieren.",
    # Popup when record is single
    "duplicate_single_title": "Duplikation bestätigen",
    "duplicate_single": "Sind Sie sicher, dass Sie diesen Datensatz duplizieren möchten?",
    # Failed Ok Popup
    "duplicate_failed_title": "Problem beim Duplizieren",
    "duplicate_failed": "Abfrage fehlgeschlagen: {exception}.",
    # Quick Editor
    "quick_edit_title": "Schnellbearbeitung - {data_key}",
}

lp_fr = {
    "button_cancel": " Annuler ",
    "button_ok": " OK ",
    "button_yes": " Oui ",
    "button_no": " Non ",
    "info_popup_title": "Info",
    # Form save_records
    # ------------------------
    "form_save_partial": "Certaines mises à jour ont été enregistrées avec succès ;",
    "form_save_problem": "Il y a eu un problème lors de l'enregistrement des mises à jour dans les tables suivantes :\n{tables}.",
    "form_save_success": "Mises à jour enregistrées avec succès.",
    "form_save_none": "Il n'y avait aucune mise à jour à enregistrer.",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "Il n'y avait aucune mise à jour à enregistrer.",
    "dataset_save_none": "Il n'y avait aucun changement à enregistrer !",
    "dataset_save_success": "Mises à jour enregistrées avec succès.",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Modifications non enregistrées",
    "form_prompt_save": "Vous avez des modifications non enregistrées !\nVoulez-vous les enregistrer avant ?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Modifications non enregistrées",
    "dataset_prompt_save": "Vous avez des modifications non enregistrées !\nVoulez-vous les enregistrer avant ?",
    # DataSet save_record
    "dataset_save_callback_false_title": "Échec de l'enregistrement (callback)",
    "dataset_save_callback_false": "Les mises à jour n'ont pas été enregistrées.",
    "dataset_save_keyed_fail_title": "Échec de l'enregistrement",
    "dataset_save_keyed_fail": "Échec de la requête : {exception}.",
    "dataset_save_fail_title": "Échec de l'enregistrement",
    "dataset_save_fail": "Échec de la requête : {exception}.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Confirmer la suppression",
    "delete_cascade": "Êtes-vous sûr de vouloir supprimer cet enregistrement?\nNotez que les enregistrements enfants:\n({children})\nseront également supprimés!",
    "delete_single": "Êtes-vous sûr de vouloir supprimer cet enregistrement?",
    # Failed Ok Popup
    "delete_failed_title": "Problème lors de la suppression",
    "delete_failed": "La requête a échoué: {exception}.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record has children
    "duplicate_child_title": "Confirmer la duplication",
    "duplicate_child": "Cet enregistrement a des enregistrements enfants:\n(dans {children})\nQuels enregistrements souhaitez-vous dupliquer?",
    "duplicate_child_button_dupparent": "Dupliquer uniquement cet enregistrement.",
    "duplicate_child_button_dupboth": "Dupliquer cet enregistrement et ses enfants.",
    # Popup when record is single
    "duplicate_single_title": "Confirmer la duplication",
    "duplicate_single": "Êtes-vous sûr de vouloir dupliquer cet enregistrement?",
    # Failed Ok Popup
    "duplicate_failed_title": "Problème lors de la duplication",
    "duplicate_failed": "La requête a échoué: {exception}.",
    # Quick Editor
    "quick_edit_title": "Édition rapide - {data_key}",
}

lp_monty_python = {
    "description_column_str_null_default": "Fresh parchment!",
    "button_cancel": "Run Away!",
    "button_ok": "It Is Good.",
    "button_yes": "Yes, My Liege.",
    "button_no": "No, Not At All.",
    "info_popup_title": "News From Castle Aaarrrggghhh",
    # Form save_records
    # ------------------------
    "form_save_partial": "Some updates were saved successfully, hooray!",
    "form_save_problem": "A problem hast occured whilst saving updates to the following tables:\n{tables}.",
    "form_save_success": "Huzzah! Thy updates hast been saved!",
    "form_save_none": "There were no updates to save. Bah!",
    # DataSet save_record
    # ------------------------
    "dataset_save_empty": "There were no updates to save. Oh, sadness!",
    "dataset_save_none": "There were no changes to save! What a surprise.",
    "dataset_save_success": "Updates saved successfully, splendid!",
    # Form prompt_save
    # ------------------------
    "form_prompt_save_title": "Unsaved Changes, Sire!",
    "form_prompt_save": "Your Majesty, thou hast unsaved changes!\nWouldst thou like to save them first?",
    # DataSet prompt_save
    # ------------------------
    "dataset_prompt_save_title": "Unsaved Changes, Sire!",
    "dataset_prompt_save": "Your Majesty, thou hast unsaved changes!\nWouldst thou like to save them first?",
    # DataSet save_record
    "dataset_save_callback_false_title": "The Knights Who Say Callback Prevented Save",
    "dataset_save_callback_false": "Updates not saved, alas!",
    "dataset_save_keyed_fail_title": "Oh, Foul Beast!",
    "dataset_save_keyed_fail": "Query hath failed: {exception}.",
    "dataset_save_fail_title": "Oh, Foul Beast!",
    "dataset_save_fail": "Query hath failed: {exception}.",
    # DataSet delete_record
    # ------------------------
    "delete_title": "Confirm Thy Deletion",
    "delete_cascade": "Art thou certain thou wishes to delete this record?\nMethinks thou should know that child records:\n({children})\nshall also meet their doom!",
    "delete_single": "Art thou certain thou wishes to delete this record?",
    # Failed Ok Popup
    "delete_failed_title": "Oh No! A Problem Hast Occurred Whilst Deleting",
    "delete_failed": "Query hath failed: {exception}.",
    # Dataset duplicate_record
    # ------------------------
    # Popup when record hath children
    "duplicate_child_title": "Confirm Duplication",
    "duplicate_child": "This record hath child records:\n(in {children})\nWhich records would thou like to duplicate?",
    "duplicate_child_button_dupparent": "Verily duplicate only this record.",
    "duplicate_child_button_dupboth": "Duplicate this record and its offspring!",
    # Popup when record is single
    "duplicate_single_title": "Confirm Duplication",
    "duplicate_single": "Art thou certain thou wishes to duplicate this record?",
    # Failed Ok Popup
    "duplicate_failed_title": "Alas! Duplicating Hath Failed",
    "duplicate_failed": "Query hath failed: {exception}.",
    # Quick Editor
    "quick_edit_title": "Haste thee! Quick Edit - {data_key}",
}
