#!/usr/bin/env python
# - coding: utf-8 -

import os
import sys
import re
import gtk
import keybinder
import ConfigParser
import gconf
import gobject
import subprocess

try:
  import dbus
  from dbus.mainloop.glib import DBusGMainLoop
except: pass

class sharkzapper_Helper:
  def __init__(self):
    
    self._NAME    = "sharkzapper Helper"
    self._VERSION = "0.4.4"
    self._AUTHORS = [
      "Intars Students\nhttp://intarstudents.lv/\n-----", 
      "ppannuto\nhttp://umich.edu/~ppannuto/\n-----", 
      "Pedro Casagrande\nhttp://launchpad.net/~pccampos\n-----", 
      "Icon by Thvg\nhttp://thvg.deviantart.com/",
      "adammw111\nhttp://github.com/adammw"
    ]
    self._INI     = os.path.expanduser('~')+"/.sharkzapper-helper"
    
    # Try to find icon file
    if os.path.exists("%s/gsd-helper.png" % sys.path[0]):
      self._ICON  = "%s/gsd-helper.png" % sys.path[0]
      
    elif os.path.exists("/usr/share/pixmaps/gsd-helper.png"):
      self._ICON  = "/usr/share/pixmaps/gsd-helper.png"
      
    else:
      # Else throw error and exit
      error_msg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, "Couldn't find icon file!")
      error_msg.run()
      
      error_msg.destroy()
      os._exit(0)
       
    # Default list of all hotkeys and their actions
    self._defaults = {
      "next"            : "<Ctrl>period",         # Ctrl + .
      "previous"        : "<Ctrl>comma",          # Ctrl + ,
      "playpause"       : "<Ctrl>equal",          # Ctrl + =
#      "shuffle"         : "<Ctrl>grave",          # Ctrl + `
#      "radio"           : "<Super>grave",         # Super + `
#      "showsongtoast"   : "<Ctrl>slash",          # Ctrl + /
#      "togglefavorite"  : "<Ctrl>backslash",      # Ctrl + \
#      "togglesmile"     : "<Super>period",        # Super + .
#      "togglefrown"     : "<Super>comma",         # Super + ,
#      "volumeup"        : "<Ctrl><Alt>Page_Up",   # Ctrl + Alt + Page Up
#      "volumedown"      : "<Ctrl><Alt>Page_Down", # Ctrl + Alt + Page Down
    }
    
    # Set default executable
    self._defaultExecutables = [
        "chromium-browser",
        "google-chrome",
    ]
    self._executable = "google-chrome"
    
    # Load default from default hotkeys
    self._hotkeys = {}
    for toggle in self._defaults:
      self._hotkeys[toggle] = self._defaults[toggle]

    # Nice names for keyboard shortcuts
    # ["toggle", ["Name in options", "(Optional) Name in menu"]]
    
    self._hotkey_name = [
      ["next"           , ["Plays next song", "Play next"]],
      ["previous"       , ["Plays previous song", "Play previous"]],
      ["playpause"      , ["Toggles Play/Pause", "Play/Pause"]],
#      ["shuffle"        , ["Toggles Shuffle", "Shuffle"]],
#      ["radio"          , ["Toggles Radio", "Radio"]],
#      ["showsongtoast"  , ["Displays song info", "Show Song Info"]],
#      ["togglefavorite" , "Favorites song"],
#      ["togglesmile"    , "\"Smiles\" song"],
#      ["togglefrown"    , "\"Frowns\" song"],
#      ["volumeup"       , "Increases volume"],
#      ["volumedown"     , "Decreases volume"],
    ]
    
    # Try to enable multimedia keys (Gnome)
    try:
      dbus_loop = DBusGMainLoop()
      self.bus = dbus.SessionBus(mainloop=dbus_loop)
      self.bus_object = self.bus.get_object('org.gnome.SettingsDaemon', '/org/gnome/SettingsDaemon/MediaKeys')
      self.bus_object.connect_to_signal("MediaPlayerKeyPressed", self.MMKeys)
    except:
      print "Multimedia keys disabled"
    
    self.load_conf()
    self.bindKeys()
    #self.protocolHandler()
    
    # Status icon stuff
    self._status_icon = gtk.StatusIcon()
    self._status_icon.set_from_file(self._ICON)
    self._status_icon.set_tooltip(self._NAME)
    self._status_icon.connect("popup-menu", self.menu_callback)
    
    gtk.main()
  
  # Add custom protocol handler
  def protocolHandler(self):
    try:
      self.gconfig = gconf.client_get_default()
      self.gconfig.set_string("/desktop/gnome/url-handlers/gs/command", "%s/Grooveshark %%s" % sys.path[0])
      self.gconfig.set_bool("/desktop/gnome/url-handlers/gs/needs_terminal", False);
      self.gconfig.set_bool("/desktop/gnome/url-handlers/gs/enabled", True);
      
    except: pass
    
  # If configuration file exists, load key combos from it 
  def load_conf(self):
    try:
      config = ConfigParser.ConfigParser()
      config.read(self._INI)
      
      for toggle in config.options("hotkeys"):
        if toggle in self._hotkeys.keys():
          self._hotkeys[toggle] = config.get("hotkeys", toggle)
          
      for executable in config.options("executables"):
        if executable == "browser":
          self._executable = config.get("executables", executable)
          
    except: pass
  
  # If possible, save to configuration file
  def save_conf(self):
    configFile = open(self._INI,"w")
    
    config = ConfigParser.ConfigParser()
    config.add_section("hotkeys")
    
    for toggle in self._hotkeys:
      config.set("hotkeys", toggle, self._hotkeys[toggle])
      
    config.add_section("executables")
    config.set("executables", "browser", self._executable)
      
    config.write(configFile)
  
  def create_conf_window(self):
    # Look and feel of window
    self._window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self._window.set_title(self._NAME)
    self._window.set_default_size(325, 200)#350
    self._window.set_icon_from_file(self._ICON)
    self._window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
    self._window.set_border_width(10)
    
    # Hooks for it (on close and key press)
    self._window.connect("destroy", self.hide_conf_window)
    self._window.connect('key-press-event', self.change_toggle)
    
    # Currently active input box
    self.modify_toggle = None
    
    # Windows box handler
    self._confWindowHandler = gtk.VBox(False, 1)
    self._confWindowHandler.show()
    
    # Build warning box
    warningLabel = gtk.Label()
    warningLabel.set_markup('\n<span size="x-small" foreground="#FFF">Keyboard shortcuts are disabled, while this window is open.</span>\n');
    warningLabel.show()
    
    warningBox = gtk.EventBox()
    warningBox.modify_bg(0, gtk.gdk.Color("#AE0000"))
    warningBox.add(warningLabel)
    warningBox.show()
    
    self._confWindowHandler.pack_end(warningBox, False)
    
    # Add nice separator
    separator = gtk.HSeparator()
    separator.show()
    
    self._confWindowHandler.pack_end(separator, False, padding=5)
    
    # Row handler
    self._confRowBox  = gtk.VBox(False, 0)
    self._confRowBox.show()
    
    rows = len(self._hotkey_name)
    table = gtk.Table(rows, 3)
    row = 0
    
    get_title = lambda x: x[0] if type(x).__name__ == "list" else x
    
    # Allow to edit each toggle
    for toggle, title in self._hotkey_name:
      label = gtk.Label(get_title(title))
      label.set_sensitive(self._hotkeys[toggle] != "DISABLED")
      label.set_alignment(0, 0.5)
      label.show()
      table.attach(label, 1, 2, row, row + 1, xpadding=5)
      
      keyval, state = gtk.accelerator_parse(self._hotkeys[toggle])
      keycombo = gtk.accelerator_get_label(keyval, state)
      
      # Input box with click event to change active toggle
      entry = gtk.Entry()
      entry.set_editable(False)
      entry.set_text(keycombo)
      entry.set_sensitive(self._hotkeys[toggle] != "DISABLED")
      entry.connect("event", self.focus_toggle, toggle, entry)
      entry.show()
      table.attach(entry, 2, 3, row, row + 1)

      # Checkbutton to enable / disable this hotkey
      # defined out of order w.r.t the table so we can pass label/entry to callback
      checkbutton = gtk.CheckButton()
      checkbutton.set_active(self._hotkeys[toggle] != "DISABLED")
      checkbutton.connect("toggled", self.checkbox_toggle, toggle, label, entry)
      checkbutton.show()
      
      table.attach(checkbutton, 0, 1, row, row + 1)
      table.set_row_spacing(row, 2)
      
      row += 1
      
    # Allow to configure executable
    label = gtk.Label("Browser Executable:")
    label.set_alignment(0, 0.5)
    label.show()
    table.attach(label, 1, 2, row, row + 1, xpadding=5)
    
    liststore = gtk.ListStore(gobject.TYPE_STRING)
    entry = gtk.ComboBoxEntry(liststore, 0)
    entry.child.set_text(self._executable)
    for executable in self._defaultExecutables:
        entry.append_text(executable)
    #entry.connect("event", self.focus_toggle, toggle, entry)
    entry.show()
    table.attach(entry, 2, 3, row, row + 1)
    self._executableEntry = entry.child
    
    table.show()
    self._confRowBox.pack_start(table)
    
    # To un-clutter windows, if new shortcuts come along, added scrollbar
    self._scrollBox = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
    self._scrollBox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    self._scrollBox.set_shadow_type(gtk.SHADOW_NONE)
    
    self._scrollBox.add_with_viewport(self._confRowBox)
    self._scrollBox.show()
    
    # Ok everything is ready, append!
    self._confWindowHandler.pack_start(self._scrollBox)
    self._window.add(self._confWindowHandler)
    self._window.show()
  
  # Enable / Disable config options
  def checkbox_toggle(self, checkbox, toggle, label, entry):
    if checkbox.get_active():
      label.set_sensitive(True)
      entry.set_sensitive(True)
      self._hotkeys[toggle] = self._defaults[toggle]
      keyval, state = gtk.accelerator_parse(self._hotkeys[toggle])
      keycombo = gtk.accelerator_get_label(keyval, state)
      entry.set_text(keycombo)
      self.save_conf()
    else:
      label.set_sensitive(False)
      entry.set_sensitive(False)
      self._hotkeys[toggle] = "DISABLED"
      self.save_conf()

  # Change toggle (if it isn't same as previous)
  def change_toggle(self, window, event):
    if self.modify_toggle != None:
      entry, toggle = self.modify_toggle
      
      keyval = event.keyval
      state = event.state
      keycombo = gtk.accelerator_get_label(keyval, state)
      new_toggle = gtk.accelerator_name(keyval, state)
      
      if not self._hotkeys[toggle] == new_toggle: 
        self._hotkeys[toggle] = new_toggle
        entry.set_text(keycombo)
        self.save_conf()
  
  # Give focus to toggle you want to change
  def focus_toggle(self, widget, event, toggle, entry, data=None):
    if event.type == gtk.gdk.BUTTON_RELEASE:
      self.modify_toggle = (entry, toggle)
  
  # Create configuration window and unbind keys
  def show_conf_window(self, window):
    self.unbindKeys()
    self.create_conf_window()
  
  # On window hide bind keys
  def hide_conf_window(self, window):
    self._executable = self._executableEntry.get_text()
    self.save_conf()
    self.bindKeys()
    self._window.hide()
  
  # Handle binding of keys
  def bindKeys(self):
    for toggle in self._hotkeys:
      if not (self._hotkeys[toggle] == "DISABLED"):
        try:  keybinder.unbind(self._hotkeys[toggle])
        except: pass
      
        # Default bad hotkeys
        if not gtk.accelerator_parse(self._hotkeys[toggle])[0] and not self._hotkeys[toggle] == self._defaults[toggle]:
          self._hotkeys[toggle] = self._defaults[toggle]
      
        try:
            keybinder.bind(self._hotkeys[toggle], self.keyboard_callback, toggle)
        
        except: pass
  
  # Handle unbinding of keys
  def unbindKeys(self):
    for toggle in self._hotkeys:  
      if not (self._hotkeys[toggle] == "DISABLED"):
        try:  keybinder.unbind(self._hotkeys[toggle])
        except: pass
  
  # Handle received hotkey action
  def keyboard_callback(self, toggle):
    if toggle == "next":
        toggle = "nextSong"
    elif toggle == "previous":
        toggle = "prevSong"
    elif toggle == "playpause":
        toggle = "togglePlayPause"
    else:
        print "Unhandled shortcut, " + toggle
        toggle = None
    if toggle:
        try:
            subprocess.call([self._executable,"--app=chrome-extension://dcaneijaapiiojfmgmdjeapgpapbjohb/html/sharkzapper_externalcommand.html#" + toggle])
        except Exception, e:
            print e


  
  # Handle multimedia keys
  def MMKeys(self, *mmkeys):
    for mmk in mmkeys:
      
      toggle = "%s" % mmk.lower()
      
      if toggle == "play":
        toggle = "playpause" 
      
      if toggle:
        self.keyboard_callback(toggle)
  
  # Handle action from context menu
  def menu_action_callback(self, widget, toggle):
    self.keyboard_callback(toggle)
  
  # Handle status icon popup
  def menu_callback(self, icon, button, time):
    menu = gtk.Menu()
    
    configure   = gtk.MenuItem("Settings")
    about       = gtk.MenuItem("About")
    quit        = gtk.MenuItem("Quit")
    separator   = gtk.MenuItem()
    
    configure.connect("activate", self.show_conf_window)
    about.connect("activate", self.show_about_dialog)
    quit.connect("activate", gtk.main_quit)
    
    menu.append(configure)
    menu.append(about)
    menu.append(quit)
    menu.append(separator)
    
    get_action = lambda x: x[1] if type(x).__name__ == "list" else x
    
    for toggle, action in self._hotkey_name:
      menu_item = gtk.MenuItem(get_action(action))
      menu_item.connect("activate", self.menu_action_callback, toggle)
      menu.append(menu_item)
    
    menu.show_all()
    menu.popup(None, None, gtk.status_icon_position_menu, button, time, self._status_icon)
  
  # Show groovy About dialog
  def show_about_dialog(self, widget):
    
    about_dialog = gtk.AboutDialog()
    
    about_dialog.set_destroy_with_parent(True)
    about_dialog.set_name(self._NAME)
    
    about_dialog.set_version(self._VERSION)
    about_dialog.set_authors(self._AUTHORS)
    about_dialog.set_website("http://sharkzapper.co.cc")
    about_dialog.set_website_label("How to groove?")
    
    icon = gtk.gdk.pixbuf_new_from_file(self._ICON)
    about_dialog.set_logo(icon)
    
    about_dialog.run()
    about_dialog.destroy()

if __name__ == '__main__':
  sharkzapper_Helper()
