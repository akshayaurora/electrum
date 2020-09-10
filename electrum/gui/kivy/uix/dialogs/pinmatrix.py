# -*- coding: utf-8 -*-
'''This module defines PinMatrixDialog.
These are used to interact with the Trezor dialog for entry
of the pin.
'''

from electrum.gui.kivy.uix.dialogs.installwizard import WizardDialog

from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.properties import StringProperty


class MatrixButton(Button):
    ''' Button used to display pin matrix
    ? ? ?
    ? ? ?
    ? ? ?
    '''
    Builder.load_string('''
<MatrixButton>
    text: '?'
    on_release:
        ti_pass = self.parent.dialog.ids.ti_pass
        ti_pass.text += str(self._intval)
''')


class PinMatrixDialog(WizardDialog):
    '''
        Displays widget with nine blank buttons and password box.
        Encodes button clicks into sequence of numbers for passing
        into PinAck messages of TREZOR.

        show_strength=True may be useful for entering new PIN
    '''
    Builder.load_string('''
<PinMatrixDialog>
    value: 'next'
    spacing: dp(9)
    SeedLabel:
        text: root.msg
        size_hint: 1, None
        height: dp(56)
    GridLayout
        id: container
        cols: 3
        rows: 3
        spacing: dp(5)
        dialog: root
    BoxLayout
        size_hint: 1, None
        height: dp(56)
        TextInput
            id: ti_pass
            focus: True
            foreground_color: 1, 1, 1, 1
            password: True
            password_mask:'ø'
            input_filter: 'int'
            padding: dp(9), dp(18), dp(9), dp(3)
            background_color: (1, 1, 1, 1)  if self.focused else (55/255., 147/255., 227/255., 1)
            background_normal: self.background_active
            background_active: 'atlas://electrum/gui/kivy/theming/light/textinput_active'
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

    msg = StringProperty('')
    '''Message to be displayed on top of dialog
    '''

    def __init__(self, **kwargs):
        self.msg = kwargs.get('msg', None)
        super(PinMatrixDialog, self).__init__(self, **kwargs)
        container = self.ids.container

        if container.children:
            #pupulate only once.
            return

        for y in range(3)[::-1]:
            for x in range(3):
                m = MatrixButton()
                m._intval = x + y * 3 + 1
                container.add_widget(m)

    def get_params(self, button):
        return (self.ids.ti_pass.text,)

    def can_go_back(self):
        return True

    def go_back(self):
        # returning None causes the plugin to cancel pin matrix.
        self.run_next(None)
