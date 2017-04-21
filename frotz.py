# Frotz.activity
# A simple front end to the classic interactive fiction interpreter frotz on the XO laptop
# http://wiki.laptop.org/go/Frotz
#
# Copyright (C) 2008  Joshua Minor
# This file is part of Frotz.activity
#
# Parts of Frotz.activity are based on code from Terminal.activity
# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>.
# Copyright (C) 2008, One Laptop Per Child
# 
#     Frotz.activity is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
# 
#     Frotz.activity is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with Frotz.activity.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

import logging
from gettext import gettext as _

import gtk
import gobject
import dbus

from sugar.activity import activity
from sugar.activity import activityfactory
from sugar import env
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.palette import Palette
import ConfigParser
import os.path
import pango

import platform, sys
from ctypes import cdll

if platform.machine().startswith('arm'):
    pass # FIXME
else:
    if platform.architecture()[0] == '64bit':
        vte_path = "x86-64"
    else:
        vte_path = "x86"
    vte = cdll.LoadLibrary("lib/%s/libvte.so.9" % vte_path)
    sys.path.append("lib/%s" % vte_path)

import vte

class FrotzActivity(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        
        logging.debug('Starting the Frotz activity')
        
        self.set_title(_('Frotz'))
        self.connect('key-press-event', self.__key_press_cb)

        toolbox = activity.ActivityToolbox(self)

        self._edit_toolbar = activity.EditToolbar()
        toolbox.add_toolbar(_('Edit'), self._edit_toolbar)
        self._edit_toolbar.show()
        self._edit_toolbar.undo.props.visible = False
        self._edit_toolbar.redo.props.visible = False
        self._edit_toolbar.separator.props.visible = False
        self._edit_toolbar.copy.connect('clicked', self._copy_cb)
        self._edit_toolbar.paste.connect('clicked', self._paste_cb)

        activity_toolbar = toolbox.get_activity_toolbar()
        activity_toolbar.share.props.visible = False
        activity_toolbar.keep.props.visible = False

        # Add a button that will send you to the ifarchive to get more games
        activity_toolbar.get_games = ToolButton('activity-get-games')
        activity_toolbar.get_games.set_tooltip(_('Get More Games'))
        activity_toolbar.get_games.connect('clicked', self._get_games_cb)
        activity_toolbar.insert(activity_toolbar.get_games, 2)
        activity_toolbar.get_games.show()

        self.set_toolbox(toolbox)
        toolbox.show()
        
        box = gtk.HBox(False, 4)

        self._vte = VTE()
        self._vte.show()
        self._vte.connect("child-exited", self._quit_cb)

        scrollbar = gtk.VScrollbar(self._vte.get_adjustment())
        scrollbar.show()

        box.pack_start(self._vte)
        box.pack_start(scrollbar, False, False, 0)
        
        self.set_canvas(box)
        box.show()
        
        self._vte.grab_focus()
        
        self.game_started = False
        default_game_file = os.path.join(activity.get_bundle_path(), "Advent.z5")
        # when we return to the idle state, launch the default game
        # if read_file is called, that will override this
        gobject.idle_add(self.start_game, default_game_file)
    
    def _quit_cb(self, foo=None):
        print "Quitting..."
        sys.exit(0)
    
    def start_game(self, game_file):
        if not self.game_started:
            # cd to a persistent directory
            # so that saved games will have a place to live
            save_dir = os.path.join(os.environ["SUGAR_ACTIVITY_ROOT"], "data")
            # print a welcome banner and pause for a moment
            # that way the end user will have a chance to see which version of frotz we are using
            # and which file we are loading

            if platform.machine().startswith('arm'):
                logging.error('ARM not supported, yet') # FIXME
                sys.exit(0)
            else:
                if platform.architecture()[0] == '64bit':
                    self._vte.feed_child("cd '%s'; clear; frotz64|head -3 ; echo '\nLoading %s...'; sleep 2; frotz64 '%s'; exit\n" % (save_dir, os.path.basename(game_file), game_file))
                else:
                    self._vte.feed_child("cd '%s'; clear; frotz32|head -3 ; echo '\nLoading %s...'; sleep 2; frotz32 '%s'; exit\n" % (save_dir, os.path.basename(game_file), game_file))
            
            self.game_started = True
        
    def read_file(self, file_path):
        self.start_game(file_path)

    def open_url(self, url):
        """Ask the journal to open an URL for us."""
        from sugar import profile
        from shutil import rmtree
        from sugar.datastore import datastore
        from sugar.activity.activity import show_object_in_journal
        from tempfile import mkdtemp
        tmpfolder = mkdtemp('.tmp', 'url', os.path.join(self.get_activity_root(), 'instance'))
        tmpfilepath = os.path.join(tmpfolder, 'url')
        try:
            tmpfile = open(tmpfilepath, 'w')
            tmpfile.write(url)
            tmpfile.close()
            os.chmod(tmpfolder, 0755)
            os.chmod(tmpfilepath, 0755)
            jobject = datastore.create()
            metadata = {
                'title': url,
                'title_set_by_user': '1',
                'buddies': '',
                'preview': '',
                'icon-color': profile.get_color().to_string(),
                'mime_type': 'text/uri-list',
            }
            for k, v in metadata.items():
                jobject.metadata[k] = v # the dict.update method is missing =(
            jobject.file_path = tmpfilepath
            datastore.write(jobject)
            show_object_in_journal(jobject.object_id)
            jobject.destroy()
        finally:
            rmtree(tmpfilepath, ignore_errors=True) # clean up!
            
    def _get_games_cb(self, button):
        url = 'http://wiki.laptop.org/go/Frotz/Games'
        #activityfactory.create_with_uri('org.laptop.WebActivity', url)
        self.open_url(url)

    def _copy_cb(self, button):
        if self._vte.get_has_selection():
            self._vte.copy_clipboard()

    def _paste_cb(self, button):
        self._vte.paste_clipboard()

    def __key_press_cb(self, window, event):
        if event.state & gtk.gdk.CONTROL_MASK and event.state & gtk.gdk.SHIFT_MASK:
        
            if gtk.gdk.keyval_name(event.keyval) == "C":
                if self._vte.get_has_selection():
                    self._vte.copy_clipboard()              
                return True
            elif gtk.gdk.keyval_name(event.keyval) == "V":
                self._vte.paste_clipboard()
                return True
                
        return False

class VTE(vte.Terminal):
    def __init__(self):
        vte.Terminal.__init__(self)
        self._configure_vte()

        #os.chdir(os.environ["HOME"])
        self.fork_command()

    def _configure_vte(self):
        conf = ConfigParser.ConfigParser()
        conf_file = os.path.join(env.get_profile_path(), 'terminalrc')
        
        if os.path.isfile(conf_file):
            f = open(conf_file, 'r')
            conf.readfp(f)
            f.close()
        else:
            conf.add_section('terminal')

        if conf.has_option('terminal', 'font'):
            font = conf.get('terminal', 'font')
        else:
            font = 'Monospace 8'
            conf.set('terminal', 'font', font)
        self.set_font(pango.FontDescription(font))

        if conf.has_option('terminal', 'fg_color'):
            fg_color = conf.get('terminal', 'fg_color')
        else:
            fg_color = '#000000'
            conf.set('terminal', 'fg_color', fg_color)
        if conf.has_option('terminal', 'bg_color'):
            bg_color = conf.get('terminal', 'bg_color')
        else:
            bg_color = '#FFFFFF'
            conf.set('terminal', 'bg_color', bg_color)
        self.set_colors(gtk.gdk.color_parse (fg_color),
                            gtk.gdk.color_parse (bg_color),
                            [])
                            
        if conf.has_option('terminal', 'cursor_blink'):
            blink = conf.getboolean('terminal', 'cursor_blink')
        else:
            blink = False
            conf.set('terminal', 'cursor_blink', blink)
        
        self.set_cursor_blinks(blink)

        if conf.has_option('terminal', 'bell'):
            bell = conf.getboolean('terminal', 'bell')
        else:
            bell = False
            conf.set('terminal', 'bell', bell)
        self.set_audible_bell(bell)
        
        if conf.has_option('terminal', 'scrollback_lines'):
            scrollback_lines = conf.getint('terminal', 'scrollback_lines')
        else:
            scrollback_lines = 1000
            conf.set('terminal', 'scrollback_lines', scrollback_lines)
            
        self.set_scrollback_lines(scrollback_lines)
        self.set_allow_bold(True)
        
        if conf.has_option('terminal', 'scroll_on_keystroke'):
            scroll_key = conf.getboolean('terminal', 'scroll_on_keystroke')
        else:
            scroll_key = False
            conf.set('terminal', 'scroll_on_keystroke', scroll_key)
        self.set_scroll_on_keystroke(scroll_key)

        if conf.has_option('terminal', 'scroll_on_output'):
            scroll_output = conf.getboolean('terminal', 'scroll_on_output')
        else:
            scroll_output = False
            conf.set('terminal', 'scroll_on_output', scroll_output)
        self.set_scroll_on_output(scroll_output)
        
        if conf.has_option('terminal', 'emulation'):
            emulation = conf.get('terminal', 'emulation')
        else:
            emulation = 'xterm'
            conf.set('terminal', 'emulation', emulation)
        self.set_emulation(emulation)

        if conf.has_option('terminal', 'visible_bell'):
            visible_bell = conf.getboolean('terminal', 'visible_bell')
        else:
            visible_bell = False
            conf.set('terminal', 'visible_bell', visible_bell)
        self.set_visible_bell(visible_bell)
        conf.write(open(conf_file, 'w'))

    def on_gconf_notification(self, client, cnxn_id, entry, what):
        self.reconfigure_vte()

    def on_vte_button_press(self, term, event):
        if event.button == 3:
            self.do_popup(event)
            return True

    def on_vte_popup_menu(self, term):
        pass
