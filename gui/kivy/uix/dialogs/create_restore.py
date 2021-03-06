''' Dialogs and widgets Responsible for creation, restoration of accounts are
defined here.

Namely: CreateAccountDialog, CreateRestoreDialog, RestoreSeedDialog
'''

from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, OptionProperty
from kivy.core.window import Window

from electrum_gui.kivy.uix.dialogs import EventsDialog
from electrum_gui.kivy.i18n import _


Builder.load_string('''
#:import Window kivy.core.window.Window
#:import _ electrum_gui.kivy.i18n._


<WizardTextInput@TextInput>
    border: 4, 4, 4, 4
    font_size: '15sp'
    padding: '15dp', '15dp'
    background_color: (1, 1, 1, 1) if self.focus else (0.454, 0.698, 0.909, 1)
    foreground_color: (0.31, 0.31, 0.31, 1) if self.focus else (0.835, 0.909, 0.972, 1)
    hint_text_color: self.foreground_color
    background_active: 'atlas://gui/kivy/theming/light/create_act_text_active'
    background_normal: 'atlas://gui/kivy/theming/light/create_act_text_active'
    size_hint_y: None
    height: '48sp'

<WizardButton@Button>:
    root: None
    size_hint: 1, None
    height: '48sp'
    on_press: if self.root: self.root.dispatch('on_press', self)
    on_release: if self.root: self.root.dispatch('on_release', self)


<-WizardDialog>
    text_color: .854, .925, .984, 1
    #auto_dismiss: False
    size_hint: None, None
    canvas.before:
        Color:
            rgba: 0, 0, 0, .9
        Rectangle:
            size: Window.size
        Color:
            rgba: .239, .588, .882, 1
        Rectangle:
            size: Window.size

    crcontent: crcontent
    # add electrum icon
    BoxLayout:
        orientation: 'vertical' if self.width < self.height else 'horizontal'
        padding:
            min(dp(42), self.width/8), min(dp(60), self.height/9.7),\
            min(dp(42), self.width/8), min(dp(72), self.height/8)
        spacing: '27dp'
        GridLayout:
            id: grid_logo
            cols: 1
            pos_hint: {'center_y': .5}
            size_hint: 1, .42
            #height: self.minimum_height
            Image:
                id: logo_img
                mipmap: True
                allow_stretch: True
                size_hint: 1, None
                height: '110dp'
                source: 'atlas://gui/kivy/theming/light/electrum_icon640'
            Widget:
                size_hint: 1, None
                height: 0 if stepper.opacity else dp(15)
            Label:
                color: root.text_color
                opacity: 0 if stepper.opacity else 1
                text: 'ELECTRUM'
                size_hint: 1, None
                height: self.texture_size[1] if self.opacity else 0
                font_size: '33sp'
                font_name: 'gui/kivy/data/fonts/tron/Tr2n.ttf'
            Image:
                id: stepper
                allow_stretch: True
                opacity: 0
                source: 'atlas://gui/kivy/theming/light/stepper_left'
                size_hint: 1, None
                height: grid_logo.height/2.5 if self.opacity else 0
        Widget:
            size_hint: None, None
            size: '5dp', '5dp'
        GridLayout:
            cols: 1
            id: crcontent
            spacing: '13dp'


<CreateRestoreDialog>
    Label:
        color: root.text_color
        size_hint: 1, None
        text_size: self.width, None
        height: self.texture_size[1]
        text:
            _("Wallet file not found!!")+"\\n\\n" +\
            _("Do you want to create a new wallet ")+\
            _("or restore an existing one?")
    Widget
        size_hint: 1, None
        height: dp(15)
    GridLayout:
        id: grid
        orientation: 'vertical'
        cols: 1
        spacing: '14dp'
        size_hint: 1, None
        height: self.minimum_height
        WizardButton:
            id: create
            text: _('Create a new seed')
            root: root
        WizardButton:
            id: restore
            text: _('I already have a seed')
            root: root


<RestoreSeedDialog>
    Label:
        color: root.text_color
        size_hint: 1, None
        text_size: self.width, None
        height: self.texture_size[1]
        text: "[b]ENTER YOUR SEED PHRASE[/b]"
    GridLayout
        cols: 1
        padding: 0, '12dp'
        orientation: 'vertical'
        spacing: '12dp'
        size_hint: 1, None
        height: self.minimum_height
        WizardTextInput:
            id: text_input_seed
            size_hint: 1, None
            height: '110dp'
            hint_text:
                _('Enter your seedphrase')
            on_text: root._trigger_check_seed()
        Label:
            font_size: '12sp'
            text_size: self.width, None
            size_hint: 1, None
            height: self.texture_size[1]
            halign: 'justify'
            valign: 'middle'
            text: root.message
            on_ref_press:
                import webbrowser
                webbrowser.open('https://electrum.org/faq.html#seed')
    GridLayout:
        rows: 1
        spacing: '12dp'
        size_hint: 1, None
        height: self.minimum_height
        WizardButton:
            id: back
            text: _('Back')
            root: root
        Button:
            id: scan
            text: _('QR')
            on_release: root.scan_seed()
        WizardButton:
            id: next
            text: _('Next')
            root: root


<ShowSeedDialog>
    spacing: '12dp'
    Label:
        color: root.text_color
        size_hint: 1, None
        text_size: self.width, None
        height: self.texture_size[1]
        text: "[b]PLEASE WRITE DOWN YOUR SEED PHRASE[/b]"

    GridLayout:
        id: grid
        cols: 1
        pos_hint: {'center_y': .5}
        size_hint_y: None
        height: dp(180)
        orientation: 'vertical'
        Button:
            border: 4, 4, 4, 4
            halign: 'justify'
            valign: 'middle'
            font_size: self.width/15
            text_size: self.width - dp(24), self.height - dp(12)
            #size_hint: 1, None
            #height: self.texture_size[1] + dp(24)
            color: .1, .1, .1, 1
            background_normal: 'atlas://gui/kivy/theming/light/white_bg_round_top'
            background_down: self.background_normal
            text: root.seed_text
        Label:
            rows: 1
            size_hint: 1, .7
            id: but_seed
            border: 4, 4, 4, 4
            halign: 'justify'
            valign: 'middle'
            font_size: self.width/21
            text: root.message
            text_size: self.width - dp(24), self.height - dp(12)
    GridLayout:
        rows: 1
        spacing: '12dp'
        size_hint: 1, None
        height: self.minimum_height
        WizardButton:
            id: back
            text: _('Back')
            root: root
        WizardButton:
            id: confirm
            text: _('Confirm')
            root: root
''')


class WizardDialog(EventsDialog):
    ''' Abstract dialog to be used as the base for all Create Account Dialogs
    '''
    crcontent = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(WizardDialog, self).__init__(**kwargs)
        self.action = kwargs.get('action')
        _trigger_size_dialog = Clock.create_trigger(self._size_dialog)
        Window.bind(size=_trigger_size_dialog,
                    rotation=_trigger_size_dialog)
        _trigger_size_dialog()
        Window.softinput_mode = 'pan'

    def _size_dialog(self, dt):
        app = App.get_running_app()
        if app.ui_mode[0] == 'p':
            self.size = Window.size
        else:
            #tablet
            if app.orientation[0] == 'p':
                #portrait
                self.size = Window.size[0]/1.67, Window.size[1]/1.4
            else:
                self.size = Window.size[0]/2.5, Window.size[1]

    def add_widget(self, widget, index=0):
        if not self.crcontent:
            super(WizardDialog, self).add_widget(widget)
        else:
            self.crcontent.add_widget(widget, index=index)

    def on_dismiss(self):
        app = App.get_running_app()
        if app.wallet is None and self._on_release is not None:
            print "on dismiss: stopping app"
            app.stop()
        else:
            Window.softinput_mode = 'below_target'


class CreateRestoreDialog(WizardDialog):
    ''' Initial Dialog for creating or restoring seed'''

    def on_parent(self, instance, value):
        if value:
            app = App.get_running_app()
            self._back = _back = partial(app.dispatch, 'on_back')


class ShowSeedDialog(WizardDialog):

    seed_text = StringProperty('')
    message = StringProperty('')

    def on_parent(self, instance, value):
        if value:
            app = App.get_running_app()
            stepper = self.ids.stepper
            stepper.opacity = 1
            stepper.source = 'atlas://gui/kivy/theming/light/stepper_full'
            self._back = _back = partial(self.ids.back.dispatch, 'on_release')


class RestoreSeedDialog(WizardDialog):

    message = StringProperty('')

    def __init__(self, **kwargs):
        super(RestoreSeedDialog, self).__init__(**kwargs)
        self._test = kwargs['test']
        self._trigger_check_seed = Clock.create_trigger(self.check_seed)

    def check_seed(self, dt):
        self.ids.next.disabled = not bool(self._test(self.get_seed_text()))

    def get_seed_text(self):
        ti = self.ids.text_input_seed
        text = unicode(ti.text).strip()
        text = ' '.join(text.split())
        return text

    def scan_seed(self):
        def on_complete(text):
            self.ids.text_input_seed.text = text
        app = App.get_running_app()
        app.scan_qr(on_complete)

    def on_parent(self, instance, value):
        if value:
            tis = self.ids.text_input_seed
            tis.focus = True
            tis._keyboard.bind(on_key_down=self.on_key_down)
            stepper = self.ids.stepper
            stepper.opacity = 1
            stepper.source = ('atlas://gui/kivy/theming'
                              '/light/stepper_restore_seed')
            self._back = _back = partial(self.ids.back.dispatch,
                                         'on_release')
            app = App.get_running_app()
            #app.navigation_higherarchy.append(_back)

    def on_key_down(self, keyboard, keycode, key, modifiers):
        if keycode[0] in (13, 271):
            self.on_enter()
            return True

    def on_enter(self):
        #self._remove_keyboard()
        # press next
        next = self.ids.next
        if not next.disabled:
            next.dispatch('on_release')

    def _remove_keyboard(self):
        tis = self.ids.text_input_seed
        if tis._keyboard:
            tis._keyboard.unbind(on_key_down=self.on_key_down)
            tis.focus = False

    def close(self):
        self._remove_keyboard()
        app = App.get_running_app()
        #if self._back in app.navigation_higherarchy:
        #    app.navigation_higherarchy.pop()
        #    self._back = None
        super(RestoreSeedDialog, self).close()
