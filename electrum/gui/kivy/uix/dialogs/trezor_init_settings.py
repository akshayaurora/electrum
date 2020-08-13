# -*- coding: utf-8 -*-
'''Module Name: `trezor_init_settings`

Purpose: provides a UI for: Initialising trezor

classes provided: TrezorInitSettingsDialog
'''

from electrum.gui.kivy.i18n import _
from electrum.gui.kivy.uix.dialogs.installwizard import WizardDialog
from electrum.plugins.trezor.trezor import (TrezorPlugin, TIM_NEW, TIM_RECOVER, TrezorInitSettings,
                     PASSPHRASE_ON_DEVICE, Capability, BackupType, RecoveryDeviceType)

from kivy.lang import Builder
from kivy.metrics import dp

SEEDLESS_MODE_WARNING  = _(
    "In seedless mode, the mnemonic seed words are never shown to the user.\n\n"
    "There is no backup, and the user has a proof of this.\n\n"
    "This is an advanced feature, only suggested to be used in redundant multisig setups.")


class TrezorInitSettingsDialog(WizardDialog):

    Builder.load_string('''
#:set PASSPHRASE_HELP_SHORT _(\
    "Passphrases allow you to access new wallets, each hidden behind"\
     "a particular case-sensitive passphrase.")
#:set PASSPHRASE_NOT_PIN _(\
    "If you forget a passphrase you will be unable to access any "\
    "bitcoins in the wallet behind it.  A passphrase is not a PIN. "\
    "Only change this if you are sure you understand it.")
#:set RECOMMEND_PIN _(\
    "Enable PIN protection, protects your bitcoins in case of theft/loss.")
<Group@BoxLayout>
    padding: dp(9), dp(4)
    canvas.before:
        Color:
            rgba: 0, 0, 0, .2
        Rectangle:
            size: self.size
            pos: self.pos

<SCheckBox@ButtonBehavior+BoxLayout>
    group: None
    active: False
    text: 'blank'
    spacing: dp(4)
    retId: None
    on_retId: if self.active: root.parent.retId = args[1]
    on_release:
        chkbx.trigger_action()
    CheckBox
        id: chkbx
        active: root.active
        group: root.group
        size_hint_x: None
        width: self.height
        allow_no_selection: False
        on_active:
            root.active = args[1]
            if args[1] == True and hasattr(root, 'retId'): root.parent.retId = root.retId
    Label
        id: lbl
        text_size: self.size
        halign: 'left'
        valign: 'center'
        text: root.text

<TrezorInitSettingsDialog>
    Group
        orientation: 'vertical'
        padding: dp(0)
        ScrollView
            GridLayout
                rows: 9
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(9)
                padding: dp(9)
                BoxLayout
                    size_hint_y: None
                    height: dp(36)
                    Label:
                        text: _('Name your device:')
                    TextInput:
                        id: ti_device_label
                        size_hint_y: None
                        height: dp(36)
                        pos_hint: {'center_y': .5}
                        background_color: (1, 1, 1, 1)  if self.focused else (1, 1, 1, .5)
                        background_normal: self.background_active
                        background_active: 'atlas://electrum/gui/kivy/theming/light/textinput_active'
                Group
                    id: gb_backup_type
                    size_hint_y: None
                    height: dp(72)
                    orientation: 'vertical'
                    Label
                        text: _('Select backup type:')
                        bold: True
                        size_hint_y: None
                        height: dp(27)
                    BoxLayout
                        id: bx_backup_type
                        SCheckBox
                            id: chk_single
                            group: 'seedtype'
                            text: _('Single Seed') + '(Bip39)'
                            active: True
                        SCheckBox
                            id: chk_shamir
                            disabled: True
                            opacity: 0
                            size_hint_x: .5
                            group: 'seedtype'
                            text: _('Shamir')
                    Widget:
                        id: spacer
                        size_hint_y: None
                        height: dp(9)
                    SCheckBox
                        id: chk_super_shamir
                        disabled: True
                        opacity: 0
                        size_hint_y: None
                        height: 0
                        group: 'seedtype'
                        text: _('Super Shamir')
                Group
                    id: gb_numwords
                    size_hint_y: None
                    height: dp(97)
                    orientation: 'vertical'
                    spacing: dp(9)
                    Label
                        id: lbl_numwords
                        text: _('Select seed length:')
                        bold: True
                        size_hint_y: None
                        height: dp(20)
                    GridLayout
                        id: bx_numwords
                        cols: 4
                        rows: 2
                SCheckBox
                    id: chk_pin
                    active: True
                    text: _(RECOMMEND_PIN)
                    size_hint_y: None
                    height: dp(40)
                ToggleButton
                    size_hint_y: None
                    height: dp(36)
                    text: _('Show expert settings') if self.state != 'down' else _('Hide expert settings')
                    on_state:
                        chk_seedless.active = chk_passphrase.active = False
                        chk_shamir.opacity = chk_super_shamir.opacity = height = 0
                        chk_super_shamir.size_hint_y = None; chk_super_shamir.height = dp(0)
                        grh = dp(72); gr.x = dp(1000)
                        if args[1] == 'down': height = gr.minimum_height; chk_shamir.opacity = chk_super_shamir.opacity = 1; grh = dp(97); gr.x = dp(10); chk_super_shamir.size_hint_y = 1
                        from kivy.animation import Animation
                        Animation(height=height).start(sv)
                        if gb_backup_type.height > 0: Animation(height = grh).start(gb_backup_type)
                StencilView
                    id: sv
                    size_hint_y: None
                    height: dp(0)
                    GridLayout:
                        id: gr
                        rows: 9
                        cols: 1
                        size: sv.width, self.minimum_height
                        pos: dp(1000), dp(10)
                        spacing: dp(9)
                        orientation: 'vertical'
                        SeedLabel
                            text: PASSPHRASE_HELP_SHORT
                        SeedLabel
                            color: 1, 0, 0, 1
                            text: PASSPHRASE_NOT_PIN
                        SCheckBox
                            id: chk_passphrase
                            size_hint_y: None
                            height: dp(45)
                            text: 'Enable passphrases'
                        SCheckBox
                            id: chk_seedless
                            tooltip: ''
                            size_hint_y: None
                            height: dp(45)
                            text: 'Enable seedless mode'
                            on_active: if sv.height > 0 and args[1] == True: root.wizard.show_error(self.tooltip)
                        Group
                            id: gb_rectype
                            size_hint_y: None
                            orientation: 'vertical'
                            height: 0
                            opacity: 0
                            Label
                                text: _('Select recovery type:')
                                bold: True
                                size_hint_y: None
                                height: dp(27)
                            BoxLayout
                                id: bx_rectype
                                SCheckBox
                                    id: chk_rec_words
                                    group: 'rectype'
                                    text: _('Scrambled Words')
                                    active: True
                                SCheckBox
                                    id: chk_rec_matrix
                                    group: 'rectype'
                                    text: _('Matrix')
''')

    def __init__(self, client, method, **kwargs):
        super(TrezorInitSettingsDialog, self).__init__(**kwargs)
        # enable next button
        self.value = 'ok'
        from kivy.factory import Factory
        # get device capabilities
        model = client.get_trezor_model()
        fw_version = client.client.version
        capabilities = client.client.features.capabilities
        have_shamir = Capability.Shamir in capabilities

        chks = self.ids.chk_shamir
        chks.retId = BackupType.Slip39_Basic
        chks.disabled = not have_shamir

        chkss = self.ids.chk_super_shamir
        chkss.retId = BackupType.Slip39_Advanced
        chkss.disabled = not Capability.ShamirGroups in capabilities

        word_count_buttons = {}
        bg_numwords = self.ids.bx_numwords
        for count in (12, 18, 20, 24, 33):
            rb = Factory.SCheckBox()
            rb.group = 'numwords'
            rb.retId = count
            word_count_buttons[count] = rb
            rb.text = _("{:d}").format(count)


        def configure_word_counts(instance=None, value=0):
            if model == "1":
                checked_wordcount = 24
            else:
                checked_wordcount = 12

            if method == TIM_RECOVER:
                if have_shamir:
                    valid_word_counts = (12, 18, 20, 24, 33)
                else:
                    valid_word_counts = (12, 18, 24)
            elif value:
                valid_word_counts = (12, 18, 24)
                self.ids.lbl_numwords.text = _('Select seed length:')
            else:
                valid_word_counts = (20, 33)
                checked_wordcount = 20
                self.ids.lbl_numwords.text = _('Select share length:')

            bg_numwords.clear_widgets()
            for btn in valid_word_counts:
                bg_numwords.add_widget(word_count_buttons[btn])
            word_count_buttons[checked_wordcount].active = True

        chk_single = self.ids.chk_single
        chk_single.bind(on_released=configure_word_counts)
        configure_word_counts(None, 1)

        # set up conditional visibility:
        # 1. backup_type is only visible when creating new seed
        # 2. word_count is not visible when recovering on TT
        gb_backup_type = self.ids.gb_backup_type
        gb_rectype = self.ids.gb_rectype

        self.ids.chk_rec_matrix.retId = None
        self.ids.chk_rec_words.retId = None

        chk_seedless = self.ids.chk_seedless
        if method == TIM_NEW:
            # show only single_seed/bip39 option by default
            gb_backup_type.height = dp(72)
            gb_backup_type.opacity = 1
            chk_single.ids.chkbx.disabled = False
            chk_single.retId = BackupType.Bip39
            chk_seedless.height = dp(45)
            chk_seedless.opacity = 1

            # check if device supports seedless mode
            if (model == '1' and fw_version >= (1, 7, 1)
                    or model == 'T' and fw_version >= (2, 0, 9)):
                chk_seedless.tooltip = SEEDLESS_MODE_WARNING
                chk_seedless.disabled = False
            else:
                cb_no_backup.disabled = True
                cb_no_backup.tooltip = _('Firmware version too old.')
        else:
            chk_seedless.height = chk_seedless.opacity = 0
            chk_seedless.disabled = True
            gb_backup_type.height = dp(0)
            gb_backup_type.opacity = 0
            self.ids.chk_single.ids.chkbx.disabled = True
            gb_numwords = self.ids.gb_numwords

            # set return Id
            self.ids.chk_rec_words.retId = RecoveryDeviceType.ScrambledWords
            self.ids.chk_rec_matrix.retId = RecoveryDeviceType.Matrix

            # show recovery_type
            gb_rectype.height = dp(90)
            gb_rectype.opacity = 1

            if model != "1":
                # hide num_words
                gb_numwords.height = dp(0)
                gb_numwords.opacity = 0
                gb_numwords.disabled = True
            else:
                # show num_words
                gb_numwords.height = dp(97)
                gb_numwords.opacity = 1
                gb_numwords.disabled = False

    def get_params(self, button):
        if button.text == 'Next':
            return (TrezorInitSettings(
                word_count=self.ids.bx_numwords.retId,
                label=self.ids.ti_device_label.text,
                pin_enabled=self.ids.chk_pin.active,
                passphrase_enabled=self.ids.chk_passphrase.active,
                recovery_type=self.ids.bx_rectype.retId,
                backup_type=self.ids.bx_backup_type.retId,
                no_backup=self.ids.chk_seedless.active if self.ids.chk_seedless.disabled == False else False,
                ), )

    def can_go_back(self):
        return True

    #def go_back(self):
        #self.run_next(None)
