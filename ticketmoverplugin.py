"""
TicketMoverPlugin:
a plugin for Trac to move tickets from one Trac instance to another
From: https://github.com/UnwashedMeme/TicketMoverPlugin
"""
import os
import shutil
import string

from trac.core import Component, TracError, implements
from trac.env import open_environment
from trac.perm import PermissionCache
from trac.ticket import Ticket
from trac.ticket.api import ITicketActionController
from trac.util.html import tag
from tracsqlhelper import get_all_dict, insert_row_from_dict


class TicketMover(Component):
    implements(ITicketActionController)

    def field_name(self, action, field):
        return "action_%s_%s" % (action, field)

    # methods for ITicketActionController
    # Extension point interface for components willing to participate
    # in the ticket workflow.
    #
    # This is mainly about controlling the changes to the ticket ''status'',
    # though not restricted to it.
    def apply_action_side_effects(self, req, ticket, action):
        """Perform side effects once all changes have been made to the ticket.

        Multiple controllers might be involved, so the apply side-effects
        offers a chance to trigger a side-effect based on the given `action`
        after the new state of the ticket has been saved.

        This method will only be called if the controller claimed to handle
        the given `action` in the call to `get_ticket_actions`.
        """
        delete = self.field_name(action, 'delete') in req.args
        project = req.args.get(self.field_name(action, 'project'))
        new_location = self.move(ticket.id, req.authname, project, delete)
        if delete:
            if new_location:
                req.redirect(new_location)
            else:
                raise TracError("Can't redirect to project {0} "
                                "after moving ticket because \"base_url\" "
                                "is not set for that project. ".format(project))

    def get_all_status(self):
        """Returns an iterable of all the possible values for the ''status''
        field this action controller knows about.

        This will be used to populate the query options and the like.
        It is assumed that the initial status of a ticket is 'new' and
        the terminal status of a ticket is 'closed'.
        """
        return []

    def get_ticket_actions(self, req, ticket):
        """Return an iterable of `(weight, action)` tuples corresponding to
        the actions that are contributed by this component.
        That list may vary given the current state of the ticket and the
        actual request parameter.

        `action` is a key used to identify that particular action.
        (note that 'history' and 'diff' are reserved and should not be used
        by plugins)

        The actions will be presented on the page in descending order of the
        integer weight. The first action in the list is used as the default
        action.

        When in doubt, use a weight of 0.
        """
        if req.perm.has_permission("TICKET_ADMIN") and len(self.projects()) > 0:
            return [(0, "move")]
        else:
            return []

    def get_ticket_changes(self, req, ticket, action):
        """Return a dictionary of ticket field changes.

        This method must not have any side-effects because it will also
        be called in preview mode (`req.args['preview']` will be set, then).
        See `apply_action_side_effects` for that. If the latter indeed triggers
        some side-effects, it is advised to emit a warning
        (`trac.web.chrome.add_warning(req, reason)`) when this method is called
        in preview mode.

        This method will only be called if the controller claimed to handle
        the given `action` in the call to `get_ticket_actions`.
        """
        return {}

    def render_ticket_action_control(self, req, ticket, action):
        """Return a tuple in the form of `(label, control, hint)`

        `label` is a short text that will be used when listing the action,
        `control` is the markup for the action control and `hint` should
        explain what will happen if this action is taken.

        This method will only be called if the controller claimed to handle
        the given `action` in the call to `get_ticket_actions`.

        Note that the radio button for the action has an `id` of
        `"action_%s" % action`.  Any `id`s used in `control` need to be made
        unique.  The method used in the default ITicketActionController is to
        use `"action_%s_something" % action`.
        """
        project_field_name = self.field_name(action, 'project')
        delete_field_name = self.field_name(action, 'delete')
        selected_project = req.args.get(project_field_name)
        controls = []
        controls.append(tag.select(
            [tag.option(p, selected=(p == selected_project or None))
             for p in self.projects()], name=project_field_name))
        controls.append(tag.label("and Delete Ticket",
                                  tag.input(type="checkbox",
                                            name=delete_field_name,
                                            checked=req.args.get(delete_field_name))))
        return ("Move To", controls, """Move to another trac. If not deleted
this ticket will be closed with resolution 'duplicate'. WARNING: references
to this ticket will not be updated.""")

    # internal methods

    _projects = None
    
    def projects(self):
        """Build the list of peer environments based upon directories
        that contain a conf/trac.ini file"""
        if self._projects is None:
            self.log.debug("Building list of peer environments")
            base_path, _project = os.path.split(self.env.path)
            p = [i for i in os.listdir(base_path)
                 if (i != _project
                     and os.path.exists(os.path.join(base_path, i, "conf/trac.ini")))]
            self._projects = sorted(p, key=string.lower)
        return self._projects

    def move(self, ticket_id, author, env, delete=False):
        """
        move a ticket to another environment

        env: environment to move to
        """
        self.log.info("Starting move of ticket %d to environment %r. delete: %r",
                      ticket_id, env, delete)

        tables = {'attachment': 'id',
                  'ticket_change': 'ticket'}

        # open the environment if it is a string
        if isinstance(env, basestring):
            base_path, _project = os.path.split(self.env.path)
            env = open_environment(os.path.join(base_path, env), use_cache=True)
            PermissionCache(env, author).require('TICKET_CREATE')

        # get the old ticket
        old_ticket = Ticket(self.env, ticket_id)

        # make a new ticket from the old ticket values
        new_ticket = Ticket(env)
        new_ticket.values = old_ticket.values.copy()
        new_ticket.insert(when=old_ticket.values['time'])
        self.log.debug("Ticket inserted into target environment as id %s",
                       new_ticket.id)

        # copy the changelog and attachment DBs
        for table, _id in tables.items():
            for row in get_all_dict(self.env,
                                    "SELECT * FROM %s WHERE %s = %%s" % (table, _id),
                                    str(ticket_id)):
                row[_id] = new_ticket.id
                insert_row_from_dict(env, table, row)
            self.log.debug("Finished copying data from %r table", table)

        # copy the attachments
        src_attachment_dir = os.path.join(
            self.env.path, 'attachments', 'ticket', str(ticket_id))
        if os.path.exists(src_attachment_dir):
            self.log.debug("Copying attachements from %r", src_attachment_dir)
            dest_attachment_dir = os.path.join(
                env.path, 'attachments', 'ticket')
            if not os.path.exists(dest_attachment_dir):
                os.makedirs(dest_attachment_dir)
            dest_attachment_dir = os.path.join(
                dest_attachment_dir, str(new_ticket.id))
            shutil.copytree(src_attachment_dir, dest_attachment_dir)

        # note the previous location on the new ticket
        if delete:
            new_ticket.save_changes(
                author, 'moved from %s (ticket deleted)' % self.env.abs_href())
        else:
            new_ticket.save_changes(
                author, 'moved from %s' % self.env.abs_href('ticket', ticket_id))
        self.log.info("Finished making new ticket @ %r",
                      env.abs_href('ticket', ticket_id))

        if delete:
            self.log.debug("Deleting old ticket")
            old_ticket.delete()
            if env.base_url:
                return env.abs_href('ticket', new_ticket.id)
        else:
            self.log.debug("Marking old ticket as duplicate.")
            # location of new ticket
            if env.base_url:
                target_name = env.abs_href('ticket', new_ticket.id)
            else:
                target_name = "{0}:#{1}".format(env.project_name, new_ticket.id)

            # close old ticket and point to new one
            old_ticket['status'] = u'closed'
            old_ticket['resolution'] = u'duplicate'
            old_ticket.save_changes(author, u'moved to %s' % target_name)
