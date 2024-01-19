import numpy as np
from math import asin
from math import pi

####################
# GENERAL PARAMETERS
####################
WAVEGUIDE_LAYER = (3, 0)
GRATING_LAYER = (4, 0)
SUS_ETCH_LAYER = (404, 0)
SLAB_PROTECTION_LAYER = (5, 0)
HEATER_FILAMENT_LAYER = (39, 0)
HEATER_CONTACT_PAD_LAYER = (41, 0)
CELL_OUTLINE_LAYER = (99, 0)
LABEL_LAYER = (100, 0)

CHIP_HEIGHT = 3000
CHIP_WIDTH = 6000
CELL_VERTICAL_SPACING = 20
CELL_HORIZONTAL_SPACING = 10

LABEL_ORIGIN = [90, -385]
LABEL_ORIGIN_HORIZONTAL = [-300, -110]
LABEL_HEIGHT = 15
LABEL_ANGLE_VERTICAL = np.pi / 2
LABEL_ANGLE_HORIZONTAL = 0

WAVEGUIDE_WIDTH = 0.5
BEND_RADIUS = 25
WG_TAPER_LENGTH = 10
WG_TAPER_WIDTH = 0.2
WG_MIN_SPACING = 10

VGA_NUM_CHANNELS = 8

SUPPORT_GAP = 0.3
SUPPORT_WIDTH = 0.25
SUPPORT_LENGTH = 3

############################
# GRATING COUPLER PARAMETERS
############################
GRATING_COUPLER_WIDTH = 0.5
GRATING_FAN_ANGLE = 2.52 #1.26  # 0.8
GRATING_TEETH_FAN_ANGLE = 3

GRATING_PERIOD_STANDARD = 0.63
GRATING_FILL_FACTOR_STANDARD = 0.5
GRATING_PERIOD_DESIGN_CENTRED = 0.63
GRATING_FILL_FACTOR_DESIGN_CENTRED = 0.5 ##################################################### TO BE CHANGED
GRATING_PERIOD_PARALLEL = 0.84 ################################################### SUBJECT TO CHANGE
GRATING_FILL_FACTOR_PARALLEL = 0.52 ################################################### SUBJECT TO CHANGE

GRATING_NO_PERIODS = 60
GRATING_TAPER_LENGTH = 350
GRATING_TAPER_ROUTE = 10
GRATING_PITCH = 127

GRATING_COUPLER_TOTAL_LENGTH = GRATING_TAPER_LENGTH + GRATING_NO_PERIODS*GRATING_PERIOD_STANDARD - GRATING_PERIOD_STANDARD*(1 - GRATING_FILL_FACTOR_STANDARD)
GRATING_COUPLER_END_WIDTH = GRATING_COUPLER_TOTAL_LENGTH*(np.sin(GRATING_FAN_ANGLE * pi/180))#GRATING_COUPLER_WIDTH


coupler_params = {
    'width': GRATING_COUPLER_WIDTH,
    'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
    'grating_period': GRATING_PERIOD_STANDARD,
    'grating_ff': GRATING_FILL_FACTOR_STANDARD,
    'n_gratings': GRATING_NO_PERIODS,
    'taper_length': GRATING_TAPER_LENGTH
}

teeth_coupler_params = {
    'width': GRATING_COUPLER_WIDTH,
    'full_opening_angle': np.deg2rad(GRATING_TEETH_FAN_ANGLE),
    'grating_period': GRATING_PERIOD_STANDARD,
    'grating_ff': GRATING_FILL_FACTOR_STANDARD,
    'n_gratings': GRATING_NO_PERIODS,
    'taper_length': GRATING_TAPER_LENGTH
}


###################
# HEATER PARAMETERS
###################
HEATER_PAD_SIZE = 70#100
HEATER_PAD_OFFSET = 20 + 2 * 5  # 2*5 compensates for rounding effects
HEATER_OVERLAP_TRI_HEIGHT = 40#50
HEATER_CONTACT_WIDTH = 40#80

################
# DBR PARAMETERS
################
DBR_WIDE_WIDTH = 0.7
DBR_NARROW_WIDTH = 0.45

#########################
# OTHER DEVICE PARAMETERS
#########################
MMI_LENGTH = 64.7
MMI_WIDTH = 12
MMI_TAPER_LENGTH = 50
MMI_TAPER_WIDTH = 5.5
MMI_INPUTS = 2
MMI_OUTPUTS = 1
MMI_GC_SPACING = 0.4
MMI_BEND_ANGLE = 0.1739
MMI_BEND_ANGLE_SPLITER = 0.31407
#MMI_BEND_ANGLE = asin(((np.sqrt(2 * ((((GC_WIDEST_POINT + MMI_GC_SPACING) / 2) - (MMI_WIDTH / 4)) ** 2))) / 2) / BEND_RADIUS))


GC_WIDEST_POINT = 10.425577

RING_RADIUS = 9.75  # NEEDS TO BE CHANGED FOR SiN

SPIRAL_GAP = 5      # NEEDS TO BE CHANGED FOR SiN
SPIRAL_INNER_GAP = 50

##########################
# HARRY'S BRAGG PARAMETERS
##########################

HK_BRAGG_PERIOD = 1.5277
BRAGG_PERIOD = 1.5277

#########################
# AIDAN'S RING PARAMETERS
#########################
AH_ring_parameters = {
    'gap': 0.25,
    'radius': 80,
    'race_length': 0
}

###########################
# AIDAN'S HEATER PARAMETERS
###########################
AH_heater_parameters = {
    'heater_trace_width': 0.9,  # Taken from Heater PDK element heating element width
    'wedge_angle': np.deg2rad(20),
    'connection_angle': np.deg2rad(10),
    'transition_wedge_height': 90,
    'transition_wedge_width': 10,
    'transition_pad_height': 70,
    'bond_pad_width': 200,
    'bond_pad_height': 200,
    'bond_join_width': 1000,
    'bond_join_height': 100
}