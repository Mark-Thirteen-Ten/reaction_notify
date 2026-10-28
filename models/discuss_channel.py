from odoo import models


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _channel_last_message_ids(self):
        """Return channel messages, not private reaction notifications."""
        if not self:
            return []
        self.env['mail.message'].flush_model()
        # Odoo 17's native batched selector, with the history filter before LIMIT.
        self.env.cr.execute(
            """
                   SELECT ARRAY_AGG(discuss_channel.id),
                          ARRAY_AGG(last_message_id)
                     FROM discuss_channel
        LEFT JOIN LATERAL (
                              SELECT id
                                FROM mail_message
                               WHERE mail_message.model = 'discuss.channel'
                                 AND mail_message.res_id = discuss_channel.id
                                 AND mail_message.message_type != 'user_notification'
                            ORDER BY id DESC
                               LIMIT 1
                          ) AS t(last_message_id) ON TRUE
                    WHERE discuss_channel.id IN %(ids)s
            """,
            {'ids': tuple(self.ids)},
        )
        channel_ids, message_ids = self.env.cr.fetchone()
        return [{'id': cid, 'message_id': mid} for cid, mid in zip(channel_ids, message_ids) if mid]
