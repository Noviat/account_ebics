# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

_FILE_FORMATS = [
    {
        "xml_id_name": "ebics_ff_C52",
        "download_process_method": "camt.052",
    },
    {
        "xml_id_name": "ebics_ff_C53",
        "download_process_method": "camt.053",
    },
    {
        "xml_id_name": "ebics_ff_FDL_camt_xxx_cfonb120_stm",
        "download_process_method": "cfonb120",
    },
]


def migrate(cr, version):
    for ff in _FILE_FORMATS:
        _update_file_format(cr, ff)


def _update_file_format(cr, ff):
    cr.execute(  # pylint: disable=E8103
        """
        SELECT res_id FROM ir_model_data
        WHERE module='account_ebics' AND name='{}'
        """.format(
            ff["xml_id_name"]
        )
    )
    res = cr.fetchone()
    if res:
        cr.execute(  # pylint: disable=E8103
            """
    UPDATE ebics_file_format
    SET download_process_method='{download_process_method}'
    WHERE id={ff_id};
            """.format(
                download_process_method=ff["download_process_method"], ff_id=res[0]
            )
        )
