import logging

from odoo import _, api, models


_logger = logging.getLogger(__name__)


class MailMessageReaction(models.Model):
    _inherit = 'mail.message.reaction'

    @api.model_create_multi
    def create(self, vals_list):
        reactions = super().create(vals_list)
        for reaction in reactions:
            reaction._notify_message_author()
        return reactions

    def _notify_message_author(self):
        self.ensure_one()
        message = self.message_id
        reactor = self.partner_id
        author = message.author_id
        if not reactor or not author or reactor == author:
            return
        if not author.user_ids.filtered('active'):
            return

        try:
            with self.env.cr.savepoint():
                self.env['mail.thread'].message_notify(
                    body=_('%(reactor)s reacted to your post with %(emoji)s',
                           reactor=reactor.name, emoji=self.content),
                    subject=_('New reaction on your post'),
                    author_id=reactor.id,
                    model=message.model,
                    res_id=message.res_id,
                    partner_ids=[author.id],
                    force_send=False,
                )
        except Exception:
            _logger.exception(
                'Unable to notify %s about reaction %s on mail.message %s',
                author.display_name, self.content, message.id,
            )