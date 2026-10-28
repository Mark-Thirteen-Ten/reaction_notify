"""Run on an isolated DB with reaction_notify installed:
odoo-bin shell -d <qa-db> --no-http < reaction_notify/checks/check_channel_preview.py
All scenario records are rolled back; no emails are sent.
"""
from odoo import Command
from odoo.exceptions import AccessError

env = globals()['env']  # Supplied by odoo-bin shell.

try:
    users = env['res.users'].with_context(
        no_reset_password=True, mail_notify_force_send=False,
    ).create([{
        'name': role,
        'login': 'reaction_preview_' + role,
        'email': role + '@example.invalid',
        'notification_type': 'inbox',
        'groups_id': [Command.set(env.ref('base.group_user').ids)],
    } for role in ('author', 'reactor', 'viewer')])
    author, reactor, viewer = users
    channel = env['discuss.channel'].create({
        'name': 'Reaction preview check',
        'channel_type': 'group',
        'channel_member_ids': [Command.create({'partner_id': u.partner_id.id}) for u in users],
    })
    original = channel.with_user(author).message_post(
        body='Shared post', message_type='comment', subtype_xmlid='mail.mt_comment',
    )
    # Match the native reaction controller's access check and elevation.
    message = original.with_user(reactor)
    assert message._validate_access_for_current_persona('write')
    message.sudo()._message_reaction('👍', 'add')
    notice = env['mail.message'].search([
        ('model', '=', 'discuss.channel'), ('res_id', '=', channel.id),
        ('message_type', '=', 'user_notification'),
    ])
    assert len(notice) == 1 and notice.id > original.id
    assert notice.partner_ids == author.partner_id
    assert notice.notification_ids.res_partner_id == author.partner_id
    assert notice.with_user(author).needaction
    assert notice.with_user(author).message_format()[0]['res_id'] == channel.id
    try:
        notice.with_user(viewer).message_format()
    except AccessError:
        pass
    else:
        raise AssertionError('Private reaction notification leaked to another member')
    for user in (viewer, author, reactor):
        previews = channel.with_user(user).channel_fetch_preview()
        assert previews[0]['last_message']['id'] == original.id
    assert env['discuss.channel']._channel_last_message_ids() == []
    print('PASS: channel previews work; reaction alert stays linked, unread and private')
finally:
    env.cr.rollback()
