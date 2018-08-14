# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    if not version:
        return

    cr.execute("select id from ebics_config")
    cfg_ids = [x[0] for x in cr.fetchall()]
    for cfg_id in cfg_ids:
        cr.execute(
            """
        SELECT DISTINCT aj.company_id
        FROM account_journal_ebics_config_rel rel
        JOIN account_journal aj ON rel.account_journal_id = aj.id
        WHERE ebics_config_id = %s
            """,
            (cfg_id,),
        )
        new_cpy_ids = [x[0] for x in cr.fetchall()]
        cr.execute(
            """
        SELECT DISTINCT res_company_id
        FROM ebics_config_res_company_rel
        WHERE ebics_config_id = %s
            """,
            (cfg_id,),
        )
        old_cpy_ids = [x[0] for x in cr.fetchall()]

        to_add = []
        for cid in new_cpy_ids:
            if cid in old_cpy_ids:
                old_cpy_ids.remove(cid)
            else:
                to_add.append(cid)
        if old_cpy_ids:
            cr.execute(
                """
          DELETE FROM ebics_config_res_company_rel
          WHERE res_company_id IN %s
            """,
                (tuple(old_cpy_ids),),
            )
        if to_add:
            for cid in to_add:
                cr.execute(
                    """
             INSERT INTO ebics_config_res_company_rel(ebics_config_id, res_company_id)
             VALUES (%s, %s);
                    """,
                    (cfg_id, cid),
                )
