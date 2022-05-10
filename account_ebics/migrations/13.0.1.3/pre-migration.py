# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

_FILE_FORMATS = [
    {
        "old_xml_id_name": "ebics_ff_camt_052_001_02_stm",
        "new_xml_id_name": "ebics_ff_C52",
        "new_name": "camt.052",
    },
    {
        "old_xml_id_name": "ebics_ff_camt_053_001_02_stm",
        "new_xml_id_name": "ebics_ff_C53",
        "new_name": "camt.053",
    },
    {
        "old_xml_id_name": "ebics_ff_camt_xxx_cfonb120_stm",
        "new_xml_id_name": "ebics_ff_FDL_camt_xxx_cfonb120_stm",
    },
    {
        "old_xml_id_name": "ebics_ff_pain_001_001_03_sct",
        "new_xml_id_name": "ebics_ff_CCT",
    },
    {
        "old_xml_id_name": "ebics_ff_pain_001",
        "new_xml_id_name": "ebics_ff_XE2",
        "new_name": "pain.001.001.03",
    },
    {
        "old_xml_id_name": "ebics_ff_pain_008_001_02_sdd",
        "new_xml_id_name": "ebics_ff_CDD",
    },
    {
        "old_xml_id_name": "ebics_ff_pain_008",
        "new_xml_id_name": "ebics_ff_XE3",
    },
    {
        "old_xml_id_name": "ebics_ff_pain_008_001_02_sbb",
        "new_xml_id_name": "ebics_ff_CDB",
    },
    {
        "old_xml_id_name": "ebics_ff_pain_001_001_02_sct",
        "new_xml_id_name": "ebics_ff_FUL_pain_001_001_02_sct",
    },
]


def migrate(cr, version):
    if not version:
        return

    for ff in _FILE_FORMATS:
        _update_file_format(cr, ff)


def _update_file_format(cr, ff):
    cr.execute(  # pylint: disable=E8103
        """
    SELECT id, res_id FROM ir_model_data
    WHERE module='account_ebics' AND name='{}'
        """.format(
            ff["old_xml_id_name"]
        )
    )
    res = cr.fetchone()
    if res:
        query = """
        UPDATE ir_model_data
        SET name='{new_xml_id_name}'
        WHERE id={xml_id};
        """.format(
            new_xml_id_name=ff["new_xml_id_name"], xml_id=res[0]
        )
        if ff.get("new_name"):
            query += """
            UPDATE ebics_file_format
            SET name='{new_name}'
            WHERE id={ff_id};
            """.format(
                new_name=ff["new_name"], ff_id=res[1]
            )
        cr.execute(query)  # pylint: disable=E8103
