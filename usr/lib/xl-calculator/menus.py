# xl-Calculator: a calculator for Linux Mint and the Cinnamon desktop.
# Copyright (C) 2026 Wesley Hayslip
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
# It is distributed WITHOUT ANY WARRANTY; see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The menus: the Buffet menu (buffet.py), every menu at once from a button in a header bar, or a
classic menu bar (Preferences → Menu).

The Buffet menu is made from the menu bar's own items each time it opens, so the two always
match: the modes shown in the Mode menu, the chosen mode, a greyed-out Print, the shortcuts."""

import buffet
from gi.repository import Gdk, GLib, Gtk
from i18n import N_, _

# How the Buffet menu looks to start with (see buffet.py): two menus in each row, as wide as the
# window, stacked up, with the shortcuts next to the items
BUFFET_DEFAULTS = {"layout": buffet.LAYOUT_FIXED, "per-row": 2, "width": buffet.WIDTH_WINDOW,
                   "no-room": buffet.NO_ROOM_MOVE, "rows": buffet.ROWS_STACKED,
                   "shortcuts": buffet.SHORTCUTS_SHOW}
BUFFET_CHOICES = {
    "layout": (buffet.LAYOUT_EQUAL, buffet.LAYOUT_FILL, buffet.LAYOUT_TWO_ROWS, buffet.LAYOUT_FIXED),
    "width": (buffet.WIDTH_WINDOW, buffet.WIDTH_SCREEN),
    "no-room": (buffet.NO_ROOM_MOVE, buffet.NO_ROOM_ROWS),
    "rows": (buffet.ROWS_LINED, buffet.ROWS_STACKED),
    "shortcuts": (buffet.SHORTCUTS_SHOW, buffet.SHORTCUTS_TOOLTIP, buffet.SHORTCUTS_HIDE),
}
MENU_COUNT = 5      # File, Edit, View, Mode, Help: the most menus a row can have

# Preferences → Menu: each setting, its name, and its choices with a note about each. The words are
# Buffet Menu's own (see buffet.PreferencesDialog), so its translations serve here too.
BUFFET_OPTIONS = (
    ("layout", N_("Menu layout"), (
        (buffet.LAYOUT_EQUAL, N_("One row, then _equal rows"),
         N_("If one row doesn't fit, as few rows as fit, with as many menus in each")),
        (buffet.LAYOUT_FILL, N_("One row, then fi_ll each row"),
         N_("If one row doesn't fit, as many menus in each row as fit")),
        (buffet.LAYOUT_TWO_ROWS, N_("T_wo rows"), N_("More rows only if two don't fit")),
        (buffet.LAYOUT_FIXED, N_("_Fixed:"), N_("Always the same number of menus in each row")))),
    ("width", N_("Row width"), (
        (buffet.WIDTH_WINDOW, N_("The application's win_dow"), N_("The menu stays inside the window when it can")),
        (buffet.WIDTH_SCREEN, N_("The scree_n"), N_("Wider rows, so fewer of them")))),
    ("no-room", N_("When there's no room below the title bar"), (
        (buffet.NO_ROOM_MOVE, N_("Move the _menu up"), N_("Above the title bar, or over it,\nwith the rows as they are")),
        (buffet.NO_ROOM_ROWS, N_("Change the _rows to fit"), N_("Below the title bar,\nwith fewer, wider rows")))),
    ("rows", N_("Rows"), (
        (buffet.ROWS_LINED, N_("Lined _up"), N_("Each row starts at the same height,\nwith a line between rows")),
        (buffet.ROWS_STACKED, N_("Stac_ked up"), N_("Each menu right under the one above it:\nshorter, but busier")))),
    ("shortcuts", N_("Keyboard shortcuts"), (
        (buffet.SHORTCUTS_SHOW, N_("_Show next to each item"), N_("As in other menus")),
        (buffet.SHORTCUTS_TOOLTIP, N_("Show in a _tooltip"), N_("Narrower menus: point at an item to see its shortcut")),
        (buffet.SHORTCUTS_HIDE, N_("_Hide"), N_("The narrowest menus")))),
)


def choice_label(label):
    """A Buffet Menu choice as a dropdown shows it: no access key, and no colon after "Fixed"."""
    return buffet.plain(_(label)).rstrip(" :\u00a0\u202f")


def choice_note(note):
    return _(note).replace("\n", " ")

style_ready = False     # buffet.set_up_style() is done once for all the windows


def checked_buffet_settings(saved):
    """The Buffet menu's settings from the settings file, each one checked: the default if it's missing or odd."""
    settings = dict(BUFFET_DEFAULTS)
    if isinstance(saved, dict):
        for key, choices in BUFFET_CHOICES.items():
            if saved.get(key) in choices:
                settings[key] = saved[key]
        per_row = saved.get("per-row")
        if isinstance(per_row, int) and 1 <= per_row <= MENU_COUNT:
            settings["per-row"] = per_row
    return settings


class BuffetMenuBar:
    """The Buffet menu and its header bar, or the menu bar: whichever Preferences → Menu chooses."""

    def set_up_menus(self, menubar, accel_group):
        """Called once the menu bar is built: gives the window its header bar and Buffet button."""
        global style_ready
        if not style_ready:
            buffet.set_up_style()
            style_ready = True
        self.menubar = menubar
        menubar.show_all()      # its items, once: the Mode menu hides the modes switched off afterwards
        self.menu_accels = accel_group
        self.buffet_accels = self.shortcuts_without_menu_bar(menubar)
        self.buffet = None
        self.buffet_items = {}      # "File → Print…": its menu bar item, which does the work
        self.buffet_shape = None    # the menus the Buffet menu was made from, to tell when they change

        self.header = Gtk.HeaderBar(show_close_button=True)
        self.buffet_button = Gtk.ToggleButton(tooltip_text=_("Menu (F10)"))
        self.buffet_button.set_image(Gtk.Image.new_from_icon_name("buffet-menu-symbolic", Gtk.IconSize.BUTTON))
        self.buffet_button.connect("toggled", self.on_buffet_toggled)
        self.header.pack_end(self.buffet_button)
        self.header.show_all()
        self.apply_menu_style()

    def apply_menu_style(self):
        """The Buffet menu in a header bar, or the menu bar under the window manager's title bar."""
        if self.buffet_on:
            self.menubar.set_no_show_all(True)      # show_all() for a new keypad leaves it hidden
            self.menubar.hide()
            if self.get_titlebar() is not self.header:
                self.set_titlebar(self.header)
            if self.buffet_accels not in Gtk.accel_groups_from_object(self):
                self.add_accel_group(self.buffet_accels)
        else:
            self.close_buffet()
            if self.buffet_accels in Gtk.accel_groups_from_object(self):
                self.remove_accel_group(self.buffet_accels)
            if self.get_titlebar() is not None:
                self.set_titlebar(None)
            self.menubar.set_no_show_all(False)
            self.menubar.show()     # not show_all(): the modes switched off stay hidden

    def shortcuts_without_menu_bar(self, menubar):
        """The menu items' keyboard shortcuts, for when the menu bar is hidden: GTK ignores a hidden menu
        item's shortcut. Each runs its item, if the menu bar would let it (not a greyed-out Print)."""
        group = Gtk.AccelGroup()

        def add(menu):
            for item in menu.get_children():
                if item.get_submenu():
                    add(item.get_submenu())
                    continue
                accel = self.accelerator_of(item)
                if accel:
                    key, mods = Gtk.accelerator_parse(accel)
                    group.connect(key, mods, Gtk.AccelFlags.VISIBLE, self.shortcut_runner(item))
        for top in menubar.get_children():
            if top.get_submenu():
                add(top.get_submenu())
        return group

    @staticmethod
    def shortcut_runner(item):
        def run(_group, _window, _key, _mods):
            if item.get_visible() and item.get_sensitive():
                item.activate()
                return True
            return False
        return run

    # --- the Buffet menu, made from the menu bar

    def accelerator_of(self, item):
        """The item's keyboard shortcut, as "<Primary>n", or None. (Its label only learns the shortcut once
        the menu has been drawn, which a hidden menu bar never is: the shortcut is looked up in the window's
        shortcuts instead.)"""
        closures = item.list_accel_closures()
        if not closures:
            return None
        key = self.menu_accels.find(lambda _key, closure, *_data: any(closure == c for c in closures))
        return Gtk.accelerator_name(key.accel_key, key.accel_mods) if key else None

    def buffet_entries(self, menu, path, items, disabled):
        """The menu's items as buffet.py lists them; notes each item by its path, and the greyed-out ones."""
        entries = []
        for item in menu.get_children():
            if not item.get_visible():
                continue
            if isinstance(item, Gtk.SeparatorMenuItem):
                if entries and entries[-1] != ("sep",):
                    entries.append(("sep",))
                continue
            label = item.get_label()
            if item.get_submenu():
                entries.append(("sub", label, self.buffet_entries(item.get_submenu(), path + [buffet.plain(label)],
                                                                  items, disabled)))
                continue
            accel = self.accelerator_of(item)
            if isinstance(item, Gtk.RadioMenuItem):     # a mode: a dot beside the one in use
                entries.append(("file", label, accel, item.get_active()))
                name = label
            elif isinstance(item, Gtk.CheckMenuItem):
                entries.append(("check", label, accel, item.get_active()))
                name = buffet.plain(label)
            else:
                entries.append(("item", label, accel))
                name = buffet.plain(label)
            item_path = " → ".join(path + [name])
            items[item_path] = item
            if not item.get_sensitive():
                disabled.add(item_path)
        while entries and entries[-1] == ("sep",):
            entries.pop()
        return entries

    def refresh_buffet(self):
        """Makes the Buffet menu again if the menus have changed since it was made."""
        menus, items, disabled = [], {}, set()
        for top in self.menubar.get_children():
            if top.get_visible() and top.get_submenu():
                title = top.get_label()
                menus.append((title, self.buffet_entries(top.get_submenu(), [buffet.plain(title)], items, disabled)))
        shape = (menus, sorted(disabled))
        if self.buffet is not None and shape == self.buffet_shape:
            return
        if self.buffet is not None:
            for popup in [self.buffet.popup] + self.buffet.sub_popups:
                popup.destroy()
        self.buffet = buffet.BuffetMenu(self.buffet_button, self.header, menus, self.on_buffet_chosen,
                                        lambda: None)
        self.buffet_items = items
        self.buffet_shape = shape
        self.apply_buffet_settings()
        self.buffet.set_disabled(disabled)

    def apply_buffet_settings(self):
        if self.buffet is None:
            return
        settings = self.buffet_settings
        self.buffet.set_layout(settings["layout"], settings["per-row"])
        self.buffet.set_width(settings["width"])
        self.buffet.set_no_room(settings["no-room"])
        self.buffet.set_rows(settings["rows"])
        self.buffet.set_shortcuts(settings["shortcuts"])

    def open_buffet(self, keyboard=False, keyval=None):
        """Opens the Buffet menu; with Alt and a letter (keyval), at the menu with that access key."""
        self.refresh_buffet()
        column = None
        if keyval is not None:
            column = next((c for c in self.buffet.columns if c.matches(keyval)), None)
            if column is None:
                return False
        self.buffet.open(keyboard=keyboard, column=column)
        return True

    def close_buffet(self):
        if self.buffet is not None:
            self.buffet.close()

    def on_buffet_toggled(self, button):
        if button.get_active():
            if self.buffet is None or not self.buffet.is_open:
                self.open_buffet()
        else:
            self.close_buffet()

    def on_buffet_chosen(self, path, accel):
        item = self.buffet_items.get(path)
        if item is not None:
            GLib.idle_add(lambda: item.activate() and False)    # once the menu has closed

    def buffet_key(self, event):
        """F10, or Alt and a menu's access key, opens the Buffet menu, as they would open the menu bar."""
        if not self.buffet_on:
            return False
        mods = event.state & Gtk.accelerator_get_default_mod_mask()
        if event.keyval == Gdk.KEY_F10 and not mods:
            return self.open_buffet(keyboard=True)
        if mods == Gdk.ModifierType.MOD1_MASK:
            return self.open_buffet(keyboard=True, keyval=event.keyval)
        return False

    # --- Preferences → Menu, in every window

    def set_buffet_on(self, on, everywhere=True):
        self.buffet_on = on
        self.apply_menu_style()
        self.save_window_settings()
        if everywhere:
            for window in self.other_calculators():
                window.set_buffet_on(on, everywhere=False)
                window.sync_preferences()

    def set_buffet_setting(self, key, value, everywhere=True):
        self.buffet_settings[key] = value
        self.apply_buffet_settings()
        self.save_window_settings()
        if everywhere:
            for window in self.other_calculators():
                window.set_buffet_setting(key, value, everywhere=False)
                window.sync_preferences()
