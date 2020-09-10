#!/usr/bin/env python3
# -*- mode: python -*-
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2016  The Electrum developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import threading
from functools import partial
from typing import TYPE_CHECKING, Union, Optional, Callable, Any

from kivy.app import App

app = App.get_running_app()

#from electrum.gui.kivy.password_dialog import PasswordLayout, PW_PASSPHRASE
from electrum.gui.kivy.main_window import ElectrumWindow
from electrum.gui.kivy.uix.dialogs.installwizard import InstallWizard
from electrum.gui.kivy.uix.dialogs.question import Question
from electrum.gui.kivy.util import TaskThread

from electrum.i18n import _
from electrum.logging import Logger
from electrum.util import parse_URI, InvalidBitcoinURI, UserCancelled, UserFacingException
from electrum.plugin import hook, DeviceUnpairableError

from kivy.clock import Clock
from kivy.logger import Logger as KivyLogger

from .plugin import OutdatedHwFirmwareException, HW_PluginBase, HardwareHandlerBase

if TYPE_CHECKING:
    from electrum.wallet import Abstract_Wallet
    from electrum.keystore import Hardware_KeyStore



class KivyHandlerBase(HardwareHandlerBase, Logger):
    '''An interface between the GUI (here, Kivy) and the device handling
    logic for handling I/O.'''

    def __init__(self,  win: Union[ElectrumWindow, InstallWizard], device: str):
        Logger.__init__(self)
        assert win.gui_thread == threading.current_thread(), 'must be called from GUI thread'
        #self.passphrase_signal.connect(self.passphrase_dialog)
        #self.word_signal.connect(self.word_dialog)
        self.win = win
        self.device = device
        self.dialog = None
        self.done = threading.Event()

    def update_status(self, paired):
        #TODO Implement paired icon on mobile
        if hasattr(self, 'button'):
            button = self.button
            icon_name = button.icon_paired if paired else button.icon_unpaired
            button.setIcon(read_QIcon(icon_name))

    def query_choice(self, msg, labels):
        #TODO adapt for kivy
        self.done.clear()
        self.win_query_choice(msg, labels)
        self.done.wait()
        return self.choice

    def yes_no_question(self, msg):
        self.done.clear()
        self.win_yes_no_question(msg)
        self.done.wait()
        return self.ok

    def show_message(self, msg, on_cancel=None):
        self.message_dialog(msg, on_cancel)

    def show_error(self, msg, blocking=False):
        self.done.clear()
        self.error_dialog(msg, blocking)
        if blocking:
            self.done.wait()

    def finished(self):
        self.clear_dialog()

    def get_word(self, msg):
        #TODO adapt for kivy
        self.done.clear()
        self.word_signal.emit(msg)
        self.done.wait()
        return self.word

    def get_passphrase(self, msg, confirm):
        #TODO adapt for kivy
        self.done.clear()
        self.passphrase_signal.emit(msg, confirm)
        self.done.wait()
        return self.passphrase

    def passphrase_dialog(self, msg, confirm):
        #TODO adapt for kivy
        #If confirm is true, require the user to enter the passphrase twice
        parent = self.top_level_window()
        d = WindowModalDialog(parent, _("Enter Passphrase"))
        if confirm:
            OK_button = OkButton(d)
            playout = PasswordLayout(msg=msg, kind=PW_PASSPHRASE, OK_button=OK_button)
            vbox = QVBoxLayout()
            vbox.addLayout(playout.layout())
            vbox.addLayout(Buttons(CancelButton(d), OK_button))
            d.setLayout(vbox)
            passphrase = playout.new_password() if d.exec_() else None
        else:
            pw = PasswordLineEdit()
            pw.setMinimumWidth(200)
            vbox = QVBoxLayout()
            vbox.addWidget(WWLabel(msg))
            vbox.addWidget(pw)
            vbox.addLayout(Buttons(CancelButton(d), OkButton(d)))
            d.setLayout(vbox)
            passphrase = pw.text() if d.exec_() else None
        self.passphrase = passphrase
        self.done.set()

    def word_dialog(self, msg):
        #TODO adapt for kivy
        dialog = WindowModalDialog(self.top_level_window(), "")
        hbox = QHBoxLayout(dialog)
        hbox.addWidget(QLabel(msg))
        text = QLineEdit()
        text.setMaximumWidth(12 * char_width_in_lineedit())
        text.returnPressed.connect(dialog.accept)
        hbox.addWidget(text)
        hbox.addStretch(1)
        dialog.exec_()  # Firmware cannot handle cancellation
        self.word = text.text()
        self.done.set()

    def message_dialog(self, msg, on_cancel):
        #Called more than once during signing, to confirm output and fee
        self.clear_dialog()
        app.show_info(msg, modal=True)

    def error_dialog(self, msg, blocking):
        def set_done():
            if blocking: self.done.set()

        Clock.schedule_once(lambda dt:
                                app.show_error(msg, on_show_error=set_done))

    def clear_dialog(self):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def win_query_choice(self, msg, labels):
        #TODO: Adapt for kivy
        def on_choice(choice):
            self.choice = choice
            self.done.set()

        ChoiceDialog(msg, labels, action=on_choice)

    def win_yes_no_question(self, msg):

        def cb(ok):
            self.ok = ok
            self.done.set()

        self.dialog = dialog = Question(msg, cb)
        dialog.auto_dismiss = False
        Clock.schedule_once(lambda dt: dialog.open())

class KivyPluginBase(object):

    @hook
    def load_wallet(self: Union['KivyPluginBase', HW_PluginBase], wallet: 'Abstract_Wallet', window: ElectrumWindow):
        relevant_keystores = [keystore for keystore in wallet.get_keystores()
                              if isinstance(keystore, self.keystore_class)]
        KivyLogger.debug('Trezor: Load_wallet')
        if not relevant_keystores:
            return
        for keystore in relevant_keystores:
            if not self.libraries_available:
                message = keystore.plugin.get_library_not_available_message()
                window.show_error(message)
                return
            tooltip = self.device + '\n' + (keystore.label or 'unnamed')
            #TODO manage icon pairing for hw_wallet for kivy UI
            #cb = partial(self._on_status_bar_button_click, window=window, keystore=keystore)
            #button = StatusBarButton(read_QIcon(self.icon_unpaired), tooltip, cb)
            #button.icon_paired = self.icon_paired
            #button.icon_unpaired = self.icon_unpaired
            #window.statusBar().addPermanentWidget(button)
            handler = self.create_handler(window)
            #handler.button = button
            keystore.handler = handler
            keystore.thread = TaskThread(window, on_error=partial(self.on_task_thread_error, window, keystore))
            self.add_show_address_on_hw_device_button_for_receive_addr(wallet, keystore, window)
        # Trigger pairings
        def trigger_pairings():
            devmgr = self.device_manager()
            devices = devmgr.scan_devices()
            # first pair with all devices that can be auto-selected
            for keystore in relevant_keystores:
                try:
                    self.get_client(keystore=keystore,
                                    force_pair=True,
                                    allow_user_interaction=False,
                                    devices=devices)
                except UserCancelled:
                    pass
            # now do manual selections
            for keystore in relevant_keystores:
                try:
                    self.get_client(keystore=keystore,
                                    force_pair=True,
                                    allow_user_interaction=True,
                                    devices=devices)
                except UserCancelled:
                    pass
            if (hasattr(window, 'info_bubble') and
                window.info_bubble): window.info_bubble.hide()

        some_keystore = relevant_keystores[0]
        some_keystore.thread.add(trigger_pairings)

    def _on_status_bar_button_click(self, *, window: ElectrumWindow, keystore: 'Hardware_KeyStore'):
        #TODO: adapt for kivy
        try:
            self.show_settings_dialog(window=window, keystore=keystore)
        except (UserFacingException, UserCancelled) as e:
            exc_info = (type(e), e, e.__traceback__)
            self.on_task_thread_error(window=window, keystore=keystore, exc_info=exc_info)

    def on_task_thread_error(self: Union['KivyPluginBase', HW_PluginBase], window: ElectrumWindow,
                             keystore: 'Hardware_KeyStore', exc_info):
        #TODO: adapt for kivy
        e = exc_info[1]
        if isinstance(e, OutdatedHwFirmwareException):
            if window.question(e.text_ignore_old_fw_and_continue(), title=_("Outdated device firmware")):
                self.set_ignore_outdated_fw()
                # will need to re-pair
                devmgr = self.device_manager()
                def re_pair_device():
                    device_id = self.choose_device(window, keystore)
                    devmgr.unpair_id(device_id)
                    self.get_client(keystore)
                keystore.thread.add(re_pair_device)
            return
        else:
            window.show_error(exc_info[1])

    def choose_device(self: Union['KivyPluginBase', HW_PluginBase], window: ElectrumWindow,
                      keystore: 'Hardware_KeyStore') -> Optional[str]:
        '''This dialog box should be usable even if the user has
        forgotten their PIN or it is in bootloader mode.'''
        #TODO adapt for kivy
        assert window.gui_thread == threading.current_thread(), 'must not be called from GUI thread'
        device_id = self.device_manager().xpub_id(keystore.xpub)
        if not device_id:
            try:
                info = self.device_manager().select_device(self, keystore.handler, keystore)
            except UserCancelled:
                return
            device_id = info.device.id_
        return device_id

    def show_settings_dialog(self, window: ElectrumWindow, keystore: 'Hardware_KeyStore') -> None:
        #TODO adapt for kivy
        # default implementation (if no dialog): just try to connect to device
        def connect():
            device_id = self.choose_device(window, keystore)
        keystore.thread.add(connect)

    def add_show_address_on_hw_device_button_for_receive_addr(self, wallet: 'Abstract_Wallet',
                                                              keystore: 'Hardware_KeyStore',
                                                              main_window: ElectrumWindow):
        # TODO for kivy: What does this do ? Can't figure out this in QT UI
        # Since this is just for display, ignoring this for now.
        # FIXME for kivy
        pass
        #plugin = keystore.plugin
        #receive_address_e = main_window.receive_address_e

        #def show_address():
            #addr = str(receive_address_e.text())
            #keystore.thread.add(partial(plugin.show_address, wallet, addr, keystore))
        #dev_name = f"{plugin.device} ({keystore.label})"
        #receive_address_e.addButton("eye1.png", show_address, _("Show on {}").format(dev_name))

    def create_handler(self, window: Union[ElectrumWindow, InstallWizard]) -> 'KivyHandlerBase':
        raise NotImplementedError()
