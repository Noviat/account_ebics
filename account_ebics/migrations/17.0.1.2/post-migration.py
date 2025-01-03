# Copyright 2009-2025 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(  # pylint: disable=E8103
        """
    UPDATE ebics_file ef
    SET state = 'done'
    FROM ebics_file_format eff
    WHERE ef.format_id = eff.id
          AND eff.type = 'down'
          AND eff.download_process_method IS NULL;
        """
    )
