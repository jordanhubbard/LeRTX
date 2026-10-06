import copy,unittest
from lertx.ui import build_application
from lertx.config import DEFAULT_PROFILE


class RoleUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=build_application([])
    def test_dots_keep_both_contrast_rings_and_selected_color(self):
        from lertx.role_ui import dot,badge,badge_ink,role_icon
        from PySide6.QtGui import QIcon
        for color in ('#000000','#ffffff','#202225','#f1f4f5'):
            image=dot(color).toImage()
            self.assertEqual(image.pixelColor(8,8).name(),color)
            self.assertLess(image.pixelColor(8,1).lightness(),70)
            self.assertGreater(image.pixelColor(8,2).lightness(),180)
            profile=copy.deepcopy(DEFAULT_PROFILE);profile['general']['leader_color']=color
            disabled=role_icon('Assign leader',profile).pixmap(16,16,QIcon.Mode.Disabled).toImage()
            self.assertEqual(disabled,role_icon('Assign leader',profile).pixmap(16,16,QIcon.Mode.Normal).toImage())
            self.assertNotEqual(badge('leader',color).toImage(),badge('follower',color).toImage())
            self.assertEqual(badge_ink(color),'#ffffff' if color in ('#000000','#202225') else '#000000')
    def test_labels_update_dots_without_changing_text_or_interpreting_plain_markup(self):
        from lertx.role_ui import widgets,badge_uri
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt
        profile=copy.deepcopy(DEFAULT_PROFILE);Label,Button,_=widgets(lambda:profile)
        label=Label();label.setTextFormat(Qt.TextFormat.PlainText)
        label.setText('Leader <script> & follower')
        self.assertEqual(label.text(),'Leader <script> & follower')
        rendered=QLabel.text(label)
        self.assertEqual(rendered.count('<img '),2)
        self.assertIn('&lt;script&gt;',rendered)
        profile['general']['leader_color']='#000000';label.refresh_role_colors()
        self.assertIn(badge_uri('leader','#000000'),QLabel.text(label))
        label.setText('New reference instructions')
        self.assertEqual(label.accessibleName(),'New reference instructions')
        button=Button('Assign leader');self.assertFalse(button.icon().isNull())
        button.setText('Connect');self.assertTrue(button.icon().isNull())
