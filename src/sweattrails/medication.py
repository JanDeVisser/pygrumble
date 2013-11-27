# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$24-Nov-2013 12:20:43 PM$"

import grumble
import sweattrails.config

class Manufacturer(grumble.Model):
    name = grumble.TextProperty(is_key = True, is_label = True)
    country = grumble.ReferenceProperty(sweattrails.config.Country)
    notes = grumble.TextProperty(multiline = True)

class Medication(grumble.Model):
    medication = grumble.TextProperty(is_key = True, is_label = True)
    manufacturer = grumble.ReferenceProperty(Manufacturer)
    description = grumble.TextProperty()
    adverse_effects = grumble.TextProperty()

class MedicationHistory(grumble.Model):
    timestamp = grumble.DateProperty(auto_now_add = True)
    current = grumble.BooleanProperty()
    medication = grumble.ReferenceProperty(Medication)
    dose = grumble.TextProperty()
    units = grumble.TextProperty("mg", "tablets", "g", "Other")
    frequency = grumble.TextProperty(choices = ["Daily", "Twice a day", "Three times a day", "Four times a day", "Other"])
    experiences = grumble.TextProperty(multiline = True)

