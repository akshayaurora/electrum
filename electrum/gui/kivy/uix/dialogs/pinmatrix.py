# -*- coding: utf-8 -*-
'''This module defines PinMatrixDialog.
These are used to interact with the Trezor dialog for entry
of the pin.
'''

from electrum_gui.kivy.uix.dialogs.installwizard import WizardDialog
from kivy.lang import Builder

class PinMatrixDialog(WizardDialog):
    '''
        Displays widget with nine blank buttons and password box.
        Encodes button clicks into sequence of numbers for passing
        into PinAck messages of TREZOR.

        show_strength=True may be useful for entering new PIN
    '''

    def __init__(self, **kwargs):
        Builder.load_string('''
<MatrixButton@Button>
    text: '?'

<PinMatrixDialog>
    value: 'next'
    spacing: dp(9)
    Label:
        text: 'Enter your current TREZOR PIN'
        size_hint: 1, None
        height: dp(56)
    GridLayout
        cols: 3
        MatrixButton
            on_release: ti_pass.text += '7'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '8'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '7'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '4'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '5'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '6'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '1'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '2'; ti_pass.focus = True
        MatrixButton
            on_release: ti_pass.text += '3'; ti_pass.focus = True
    BoxLayout
        size_hint: 1, None
        height: dp(56)
        TextInput
            id: ti_pass
            focus: True
            foreground_color: 1, 1, 1, 1
            password: True
            #password_mask:'ø'
            input_filter: 'int'
            padding: dp(9), dp(18), dp(9), dp(3)
            background_color: (1, 1, 1, 1)  if self.focused else (55/255., 147/255., 227/255., 1)
            background_normal: self.background_active
            background_active: 'atlas://gui/kivy/theming/light/textinput_active'
            on_text:
                import math
                digits = len(set(str(self.text)))
                strength = math.factorial(9) / math.factorial(9 - digits)
                lbl_password_strength.text = 'Weak' if strength < 3000 else ('Fine' if strength < 60000 else ('Strong' if strength < 360000 else 'Ultimate'))
        Label:
            id: lbl_password_strength
            bold : True
            color: {'Weak': (1, 0, 0, 1), 'Fine': (1, 1, 1, 1), 'Strong': (0, 1, 0, 1), 'Ultimate': (0, 0, 1, 1)}[self.text] if self.text else (1, 1, 1, 1)
            text: 'Weak'
''')
        super(PinMatrixDialog, self).__init__(self, **kwargs)


    def can_go_back(self):
        return True

    def go_back(self):
        # do nothing when going back
        # dialog is alredy closed, just return
        print 'TODO go before pin dialog'
        return
