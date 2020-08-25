from functools import partial
import threading

from electrum.i18n import _
from electrum.plugin import hook
from electrum.util import bh2u, UserFacingException
from electrum.base_wizard import (HWD_SETUP_NEW_WALLET, ChooseHwDeviceAgain,
    UserFacingException, UserCancelled, GoBack, OutdatedHwFirmwareException,
    ScriptTypeNotSupported)

from ..hw_wallet.kivy import KivyHandlerBase, KivyPluginBase
from ..hw_wallet.plugin import only_hook_if_libraries_available
from .trezor import (TrezorPlugin, TIM_NEW, TIM_RECOVER, TrezorInitSettings,
                     PASSPHRASE_ON_DEVICE, Capability, BackupType, RecoveryDeviceType)


from kivy.app import App
app = App.get_running_app()

from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.logger import Logger

PASSPHRASE_HELP_SHORT =_(
    "Passphrases allow you to access new wallets, each "
    "hidden behind a particular case-sensitive passphrase.")
PASSPHRASE_HELP = PASSPHRASE_HELP_SHORT + "  " + _(
    "You need to create a separate Electrum wallet for each passphrase "
    "you use as they each generate different addresses.  Changing "
    "your passphrase does not lose other wallets, each is still "
    "accessible behind its own passphrase.")
PASSPHRASE_NOT_PIN = _(
    "If you forget a passphrase you will be unable to access any "
    "bitcoins in the wallet behind it.  A passphrase is not a PIN. "
    "Only change this if you are sure you understand it.")
MATRIX_RECOVERY = _(
    "Enter the recovery words by pressing the buttons according to what "
    "the device shows on its display.  You can also use your NUMPAD.\n"
    "Press BACKSPACE to go back a choice or word.\n")


class KivyHandler(KivyHandlerBase):
    '''
    '''

    def __init__(self, win, pin_matrix_dialog, device):
        super(KivyHandler, self).__init__(win, device)
        self.pin_matrix_dialog = pin_matrix_dialog
        #self.matrix_signal.connect(self.matrix_recovery_dialog)
        #self.matrix_dialog = None
        #self.passphrase_on_device = False

    def get_pin(self, msg, *, show_strength=True):
        self.done.clear()
        self.pin_dialog(msg, show_strength)
        self.done.wait()
        return self.response

    def get_matrix(self, msg):
        self.done.clear()
        self.matrix_signal.emit(msg)
        self.done.wait()
        data = self.matrix_dialog.data
        if data == 'x':
            self.close_matrix_dialog()
        return data

    def close_matrix_dialog(self):
        self.clear_dialog()

    def pin_dialog(self, msg, show_strength):
        # Needed e.g. when resetting a device ??
        self.clear_dialog()

        def set_response(value):
            self.response = value
            if value: self.show_message(_('Waiting for Pin'))
            self.done.set()

        dialog = self.pin_matrix_dialog(
            msg=msg, run_next=set_response)
        self.dialog = dialog
        # open the dialog in GUI/Main thread
        Clock.schedule_once(lambda dt: dialog.open())


    def matrix_recovery_dialog(self, msg):
        if not self.matrix_dialog:
            self.matrix_dialog = MatrixDialog(self.top_level_window())
        self.matrix_dialog.get_matrix(msg)
        self.done.set()

    def passphrase_dialog(self, msg, confirm):
        #If confirm is true, require the user to enter the passphrase twice
        parent = self.top_level_window()
        d = WindowModalDialog(parent, _('Enter Passphrase'))

        OK_button = OkButton(d, _('Enter Passphrase'))
        OnDevice_button = QPushButton(_('Enter Passphrase on Device'))

        new_pw = PasswordLineEdit()
        conf_pw = PasswordLineEdit()

        vbox = QVBoxLayout()
        label = QLabel(msg + "\n")
        label.setWordWrap(True)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(0, 150)
        grid.setColumnMinimumWidth(1, 100)
        grid.setColumnStretch(1,1)

        vbox.addWidget(label)

        grid.addWidget(QLabel(_('Passphrase:')), 0, 0)
        grid.addWidget(new_pw, 0, 1)

        if confirm:
            grid.addWidget(QLabel(_('Confirm Passphrase:')), 1, 0)
            grid.addWidget(conf_pw, 1, 1)

        vbox.addLayout(grid)

        def enable_OK():
            if not confirm:
                ok = True
            else:
                ok = new_pw.text() == conf_pw.text()
            OK_button.setEnabled(ok)

        new_pw.textChanged.connect(enable_OK)
        conf_pw.textChanged.connect(enable_OK)

        vbox.addWidget(OK_button)

        if self.passphrase_on_device:
            vbox.addWidget(OnDevice_button)

        d.setLayout(vbox)

        self.passphrase = None

        def ok_clicked():
            self.passphrase = new_pw.text()

        def on_device_clicked():
            self.passphrase = PASSPHRASE_ON_DEVICE

        OK_button.clicked.connect(ok_clicked)
        OnDevice_button.clicked.connect(on_device_clicked)
        OnDevice_button.clicked.connect(d.accept)

        d.exec_()
        self.done.set()


class KivyPlugin(KivyPluginBase):
    # Derived classes must provide the following class-static variables:
    #   icon_file
    #   pin_matrix_widget_class

    @only_hook_if_libraries_available
    @classmethod
    @hook
    def receive_menu(self, menu, addrs, wallet):
        if len(addrs) != 1:
            return
        for keystore in wallet.get_keystores():
            if type(keystore) == self.keystore_class:
                def show_address(keystore=keystore):
                    keystore.thread.add(partial(self.show_address, wallet, addrs[0], keystore))
                device_name = "{} ({})".format(self.device, keystore.label)
                menu.addAction(_("Show on {}").format(device_name), show_address)

    def show_settings_dialog(self, window, keystore):
        def connect():
            device_id = self.choose_device(window, keystore)
            return device_id
        def show_dialog(device_id):
            if device_id:
                SettingsDialog(window, self, keystore, device_id).exec_()
        keystore.thread.add(connect, on_success=show_dialog)

    def request_trezor_init_settings(self, wizard, method, device_id,
                                     run_next=None):
        # initialize device screen/flow
        from electrum.gui.kivy.uix.dialogs.trezor_init_settings\
            import TrezorInitSettingsDialog
        # get device details
        devmgr = self.device_manager()
        client = devmgr.client_by_id(device_id)
        if not client:
            wizard.show_error(_("The device was disconnected."))
            return wizard.choose_hw_device()

        TrezorInitSettingsDialog(client, method, wizard=wizard, run_next=run_next).open()


class Plugin(TrezorPlugin, KivyPlugin):
    icon_unpaired = "trezor_unpaired.png"
    icon_paired = "trezor.png"

    def scan_and_create_client_for_device(self, device_id: str, wizard: 'BaseWizard',
                                          run_next=None):

        def set_client_id():
            devmgr = self.device_manager()
            client = devmgr.client_by_id(device_id)
            Clock.schedule_once(lambda dt: run_next(client))

        wizard.run_task_without_blocking_gui(task=set_client_id)

    def _safe_on_client(self, client, wizard: 'BaseWizard', device_info, device_id, purpose, run_next=None):
        if client is None:
            raise UserFacingException(
                _('Failed to create a client for this device.') + '\n' +
                _('Make sure it is in the correct state.'))
        client.handler = self.create_handler(wizard)
        # check_client
        if not client.is_uptodate():
            msg = (_('Outdated {} firmware for device labelled {}. Please '
                     'download the updated firmware from {}')
                   .format(self.device, client.label(), self.firmware_URL))
            raise OutdatedHwFirmwareException(msg)

        def run_get_xpub():
            is_creating_wallet = purpose == HWD_SETUP_NEW_WALLET

            def _next(_client, _purpose):
                _client.used()
                run_next(_client, _purpose)

            wizard.run_task_without_blocking_gui(
                task=lambda: 
                    client.get_xpub('m', 'standard', creating=is_creating_wallet),
                on_finished=partial(_next, client, purpose),
                go_back=partial(wizard.choose_hw_device))

        if not device_info.initialized:
            self.initialize_device(device_id, wizard, client.handler,
                                   run_next=run_get_xpub)
            return
        run_get_xpub()


    def initialize_device(self, device_id, wizard, handler, run_next=None):
        # Initialization method
        msg = _("Choose how you want to initialize your {}.").format(self.device, self.device)
        choices = [
            (TIM_NEW, _("Let the device generate a completely new seed randomly")),
            (TIM_RECOVER, _("Recover from a seed you have previously written down")),
        ]
        def f(method, settings):
            wizard.run_task_without_blocking_gui(partial(
                self._initialize_device_safe, settings,
                method, device_id, wizard, handler, run_next=run_next))

        wizard.choice_dialog(
            title=_('Initialize Device'), message=msg, choices=choices,
            run_next=lambda method:
                self.request_trezor_init_settings(
                    wizard, method, device_id, run_next=partial(f, method)))

    def _initialize_device_safe(self, settings, method, device_id, wizard, handler, run_next=None):
        exit_code = delay = 0
        try:
            self._initialize_device(settings, method, device_id, wizard, handler)
        except UserCancelled:
            exit_code = 1
        except BaseException as e:
            Logger.debug('Trezor: {}'.format(e))
            handler.show_error(repr(e))
            exit_code = delay = 1
        finally:
            if exit_code == 1:
                Clock.schedule_once(lambda dt: wizard.choose_hw_device(), delay)
                return
            # run get_xpub
            Clock.schedule_once(lambda dt: run_next())

    # override setup_device for trezor acc to kivy
    def setup_device(self, device_info, wizard, purpose, run_next=None):
        device_id = device_info.device.id_

        def on_client(client):
            try:
                self._safe_on_client(client, wizard, device_info,
                                     device_id, purpose, run_next=run_next)
            except OSError as e:
                wizard.show_error(
                    _('We encountered an error while connecting to your device:')
                    + '\n' + str(e) + '\n'
                    + _('To try to fix this, we will now re-pair with your device.') + '\n'
                    + _('Please try again.'))
                devmgr.unpair_id(device_info.device.id_)
                wizard.choose_hw_device()
            except OutdatedHwFirmwareException as e:
                if wizard.question(e.text_ignore_old_fw_and_continue(), title=_("Outdated device firmware")):
                    wizard.plugin.set_ignore_outdated_fw()
                    # will need to re-pair
                    devmgr.unpair_id(device_info.device.id_)
                wizard.choose_hw_device()
            except (UserCancelled, GoBack):
                wizard.choose_hw_device()
            except UserFacingException as e:
                wizard.show_error(str(e))
                wizard.choose_hw_device()
            except BaseException as e:
                wizard.logger.exception('')
                wizard.show_error(str(e))
                wizard.choose_hw_device()

        self.scan_and_create_client_for_device(
            device_id=device_id, wizard=wizard, run_next=on_client)

    def get_xpub(self, device_id, derivation, xtype, wizard, run_next=None):
        if xtype not in self.SUPPORTED_XTYPES:
            raise ScriptTypeNotSupported(_('This type of script is not supported with {}.').format(self.device))

        def on_client(client):
            if client is None:
                wizard.show_error(
                    _('Failed to create a client for this device.') + '\n' +
                    _('Make sure it is in the correct state.'))
                return wizard.choose_hw_device()
            xpub = client.get_xpub(derivation, xtype)
            client.used()
            run_next(xpub)

        self.scan_and_create_client_for_device(
            device_id=device_id, wizard=wizard, run_next=on_client)

    def create_handler(self, window):
        return KivyHandler(window, self.pin_matrix_widget_class(), self.device)

    def pin_matrix_widget_class(self):
        from electrum.gui.kivy.uix.dialogs.pinmatrix import PinMatrixDialog
        return PinMatrixDialog


#class SettingsDialog(WindowModalDialog):
    #'''This dialog doesn't require a device be paired with a wallet.
    #We want users to be able to wipe a device even if they've forgotten
    #their PIN.'''

    #def __init__(self, window, plugin, keystore, device_id):
        #title = _("{} Settings").format(plugin.device)
        #super(SettingsDialog, self).__init__(window, title)
        #self.setMaximumWidth(540)

        #devmgr = plugin.device_manager()
        #config = devmgr.config
        #handler = keystore.handler
        #thread = keystore.thread
        #hs_cols, hs_rows = (128, 64)

        #def invoke_client(method, *args, **kw_args):
            #unpair_after = kw_args.pop('unpair_after', False)

            #def task():
                #client = devmgr.client_by_id(device_id)
                #if not client:
                    #raise RuntimeError("Device not connected")
                #if method:
                    #getattr(client, method)(*args, **kw_args)
                #if unpair_after:
                    #devmgr.unpair_id(device_id)
                #return client.features

            #thread.add(task, on_success=update)

        #def update(features):
            #self.features = features
            #set_label_enabled()
            #if features.bootloader_hash:
                #bl_hash = bh2u(features.bootloader_hash)
                #bl_hash = "\n".join([bl_hash[:32], bl_hash[32:]])
            #else:
                #bl_hash = "N/A"
            #noyes = [_("No"), _("Yes")]
            #endis = [_("Enable Passphrases"), _("Disable Passphrases")]
            #disen = [_("Disabled"), _("Enabled")]
            #setchange = [_("Set a PIN"), _("Change PIN")]

            #version = "%d.%d.%d" % (features.major_version,
                                    #features.minor_version,
                                    #features.patch_version)

            #device_label.setText(features.label)
            #pin_set_label.setText(noyes[features.pin_protection])
            #passphrases_label.setText(disen[features.passphrase_protection])
            #bl_hash_label.setText(bl_hash)
            #label_edit.setText(features.label)
            #device_id_label.setText(features.device_id)
            #initialized_label.setText(noyes[features.initialized])
            #version_label.setText(version)
            #clear_pin_button.setVisible(features.pin_protection)
            #clear_pin_warning.setVisible(features.pin_protection)
            #pin_button.setText(setchange[features.pin_protection])
            #pin_msg.setVisible(not features.pin_protection)
            #passphrase_button.setText(endis[features.passphrase_protection])
            #language_label.setText(features.language)

        #def set_label_enabled():
            #label_apply.setEnabled(label_edit.text() != self.features.label)

        #def rename():
            #invoke_client('change_label', label_edit.text())

        #def toggle_passphrase():
            #title = _("Confirm Toggle Passphrase Protection")
            #currently_enabled = self.features.passphrase_protection
            #if currently_enabled:
                #msg = _("After disabling passphrases, you can only pair this "
                        #"Electrum wallet if it had an empty passphrase.  "
                        #"If its passphrase was not empty, you will need to "
                        #"create a new wallet with the install wizard.  You "
                        #"can use this wallet again at any time by re-enabling "
                        #"passphrases and entering its passphrase.")
            #else:
                #msg = _("Your current Electrum wallet can only be used with "
                        #"an empty passphrase.  You must create a separate "
                        #"wallet with the install wizard for other passphrases "
                        #"as each one generates a new set of addresses.")
            #msg += "\n\n" + _("Are you sure you want to proceed?")
            #if not self.question(msg, title=title):
                #return
            #invoke_client('toggle_passphrase', unpair_after=currently_enabled)

        #def change_homescreen():
            #dialog = QFileDialog(self, _("Choose Homescreen"))
            #filename, __ = dialog.getOpenFileName()
            #if not filename:
                #return  # user cancelled

            #if filename.endswith('.toif'):
                #img = open(filename, 'rb').read()
                #if img[:8] != b'TOIf\x90\x00\x90\x00':
                    #handler.show_error('File is not a TOIF file with size of 144x144')
                    #return
            #else:
                #from PIL import Image # FIXME
                #im = Image.open(filename)
                #if im.size != (128, 64):
                    #handler.show_error('Image must be 128 x 64 pixels')
                    #return
                #im = im.convert('1')
                #pix = im.load()
                #img = bytearray(1024)
                #for j in range(64):
                    #for i in range(128):
                        #if pix[i, j]:
                            #o = (i + j * 128)
                            #img[o // 8] |= (1 << (7 - o % 8))
                #img = bytes(img)
            #invoke_client('change_homescreen', img)

        #def clear_homescreen():
            #invoke_client('change_homescreen', b'\x00')

        #def set_pin():
            #invoke_client('set_pin', remove=False)

        #def clear_pin():
            #invoke_client('set_pin', remove=True)

        #def wipe_device():
            #wallet = window.wallet
            #if wallet and sum(wallet.get_balance()):
                #title = _("Confirm Device Wipe")
                #msg = _("Are you SURE you want to wipe the device?\n"
                        #"Your wallet still has bitcoins in it!")
                #if not self.question(msg, title=title,
                                     #icon=QMessageBox.Critical):
                    #return
            #invoke_client('wipe_device', unpair_after=True)

        #def slider_moved():
            #mins = timeout_slider.sliderPosition()
            #timeout_minutes.setText(_("{:2d} minutes").format(mins))

        #def slider_released():
            #config.set_session_timeout(timeout_slider.sliderPosition() * 60)

        #Information tab
        #info_tab = QWidget()
        #info_layout = QVBoxLayout(info_tab)
        #info_glayout = QGridLayout()
        #info_glayout.setColumnStretch(2, 1)
        #device_label = QLabel()
        #pin_set_label = QLabel()
        #passphrases_label = QLabel()
        #version_label = QLabel()
        #device_id_label = QLabel()
        #bl_hash_label = QLabel()
        #bl_hash_label.setWordWrap(True)
        #language_label = QLabel()
        #initialized_label = QLabel()
        #rows = [
            #(_("Device Label"), device_label),
            #(_("PIN set"), pin_set_label),
            #(_("Passphrases"), passphrases_label),
            #(_("Firmware Version"), version_label),
            #(_("Device ID"), device_id_label),
            #(_("Bootloader Hash"), bl_hash_label),
            #(_("Language"), language_label),
            #(_("Initialized"), initialized_label),
        #]
        #for row_num, (label, widget) in enumerate(rows):
            #info_glayout.addWidget(QLabel(label), row_num, 0)
            #info_glayout.addWidget(widget, row_num, 1)
        #info_layout.addLayout(info_glayout)

        #Settings tab
        #settings_tab = QWidget()
        #settings_layout = QVBoxLayout(settings_tab)
        #settings_glayout = QGridLayout()

        #Settings tab - Label
        #label_msg = QLabel(_("Name this {}.  If you have multiple devices "
                             #"their labels help distinguish them.")
                           #.format(plugin.device))
        #label_msg.setWordWrap(True)
        #label_label = QLabel(_("Device Label"))
        #label_edit = QLineEdit()
        #label_edit.setMinimumWidth(150)
        #label_edit.setMaxLength(plugin.MAX_LABEL_LEN)
        #label_apply = QPushButton(_("Apply"))
        #label_apply.clicked.connect(rename)
        #label_edit.textChanged.connect(set_label_enabled)
        #settings_glayout.addWidget(label_label, 0, 0)
        #settings_glayout.addWidget(label_edit, 0, 1, 1, 2)
        #settings_glayout.addWidget(label_apply, 0, 3)
        #settings_glayout.addWidget(label_msg, 1, 1, 1, -1)

        #Settings tab - PIN
        #pin_label = QLabel(_("PIN Protection"))
        #pin_button = QPushButton()
        #pin_button.clicked.connect(set_pin)
        #settings_glayout.addWidget(pin_label, 2, 0)
        #settings_glayout.addWidget(pin_button, 2, 1)
        #pin_msg = QLabel(_("PIN protection is strongly recommended.  "
                           #"A PIN is your only protection against someone "
                           #"stealing your bitcoins if they obtain physical "
                           #"access to your {}.").format(plugin.device))
        #pin_msg.setWordWrap(True)
        #pin_msg.setStyleSheet("color: red")
        #settings_glayout.addWidget(pin_msg, 3, 1, 1, -1)

        #Settings tab - Homescreen
        #homescreen_label = QLabel(_("Homescreen"))
        #homescreen_change_button = QPushButton(_("Change..."))
        #homescreen_clear_button = QPushButton(_("Reset"))
        #homescreen_change_button.clicked.connect(change_homescreen)
        #try:
            #import PIL
        #except ImportError:
            #homescreen_change_button.setDisabled(True)
            #homescreen_change_button.setToolTip(
                #_("Required package 'PIL' is not available - Please install it or use the Trezor website instead.")
            #)
        #homescreen_clear_button.clicked.connect(clear_homescreen)
        #homescreen_msg = QLabel(_("You can set the homescreen on your "
                                  #"device to personalize it.  You must "
                                  #"choose a {} x {} monochrome black and "
                                  #"white image.").format(hs_cols, hs_rows))
        #homescreen_msg.setWordWrap(True)
        #settings_glayout.addWidget(homescreen_label, 4, 0)
        #settings_glayout.addWidget(homescreen_change_button, 4, 1)
        #settings_glayout.addWidget(homescreen_clear_button, 4, 2)
        #settings_glayout.addWidget(homescreen_msg, 5, 1, 1, -1)

        #Settings tab - Session Timeout
        #timeout_label = QLabel(_("Session Timeout"))
        #timeout_minutes = QLabel()
        #timeout_slider = QSlider(Qt.Horizontal)
        #timeout_slider.setRange(1, 60)
        #timeout_slider.setSingleStep(1)
        #timeout_slider.setTickInterval(5)
        #timeout_slider.setTickPosition(QSlider.TicksBelow)
        #timeout_slider.setTracking(True)
        #timeout_msg = QLabel(
            #_("Clear the session after the specified period "
              #"of inactivity.  Once a session has timed out, "
              #"your PIN and passphrase (if enabled) must be "
              #"re-entered to use the device."))
        #timeout_msg.setWordWrap(True)
        #timeout_slider.setSliderPosition(config.get_session_timeout() // 60)
        #slider_moved()
        #timeout_slider.valueChanged.connect(slider_moved)
        #timeout_slider.sliderReleased.connect(slider_released)
        #settings_glayout.addWidget(timeout_label, 6, 0)
        #settings_glayout.addWidget(timeout_slider, 6, 1, 1, 3)
        #settings_glayout.addWidget(timeout_minutes, 6, 4)
        #settings_glayout.addWidget(timeout_msg, 7, 1, 1, -1)
        #settings_layout.addLayout(settings_glayout)
        #settings_layout.addStretch(1)

        #Advanced tab
        #advanced_tab = QWidget()
        #advanced_layout = QVBoxLayout(advanced_tab)
        #advanced_glayout = QGridLayout()

        #Advanced tab - clear PIN
        #clear_pin_button = QPushButton(_("Disable PIN"))
        #clear_pin_button.clicked.connect(clear_pin)
        #clear_pin_warning = QLabel(
            #_("If you disable your PIN, anyone with physical access to your "
              #"{} device can spend your bitcoins.").format(plugin.device))
        #clear_pin_warning.setWordWrap(True)
        #clear_pin_warning.setStyleSheet("color: red")
        #advanced_glayout.addWidget(clear_pin_button, 0, 2)
        #advanced_glayout.addWidget(clear_pin_warning, 1, 0, 1, 5)

        #Advanced tab - toggle passphrase protection
        #passphrase_button = QPushButton()
        #passphrase_button.clicked.connect(toggle_passphrase)
        #passphrase_msg = WWLabel(PASSPHRASE_HELP)
        #passphrase_warning = WWLabel(PASSPHRASE_NOT_PIN)
        #passphrase_warning.setStyleSheet("color: red")
        #advanced_glayout.addWidget(passphrase_button, 3, 2)
        #advanced_glayout.addWidget(passphrase_msg, 4, 0, 1, 5)
        #advanced_glayout.addWidget(passphrase_warning, 5, 0, 1, 5)

        #Advanced tab - wipe device
        #wipe_device_button = QPushButton(_("Wipe Device"))
        #wipe_device_button.clicked.connect(wipe_device)
        #wipe_device_msg = QLabel(
            #_("Wipe the device, removing all data from it.  The firmware "
              #"is left unchanged."))
        #wipe_device_msg.setWordWrap(True)
        #wipe_device_warning = QLabel(
            #_("Only wipe a device if you have the recovery seed written down "
              #"and the device wallet(s) are empty, otherwise the bitcoins "
              #"will be lost forever."))
        #wipe_device_warning.setWordWrap(True)
        #wipe_device_warning.setStyleSheet("color: red")
        #advanced_glayout.addWidget(wipe_device_button, 6, 2)
        #advanced_glayout.addWidget(wipe_device_msg, 7, 0, 1, 5)
        #advanced_glayout.addWidget(wipe_device_warning, 8, 0, 1, 5)
        #advanced_layout.addLayout(advanced_glayout)
        #advanced_layout.addStretch(1)

        #tabs = QTabWidget(self)
        #tabs.addTab(info_tab, _("Information"))
        #tabs.addTab(settings_tab, _("Settings"))
        #tabs.addTab(advanced_tab, _("Advanced"))
        #dialog_vbox = QVBoxLayout(self)
        #dialog_vbox.addWidget(tabs)
        #dialog_vbox.addLayout(Buttons(CloseButton(self)))

        #Update information
        #invoke_client(None)
