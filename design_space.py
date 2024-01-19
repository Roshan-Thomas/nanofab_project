import numpy as np
from math import pi
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.coupler import GratingCoupler
from shapely.geometry import Polygon
from gdshelpers.layout import GridLayout

from components import *
from parameters import *

# Path where you want your GDS to be saved to
savepath = r"./"

x_coords = 0
x_coords_max = CHIP_WIDTH

# ---------------------------------------------------------------------------------------------------------------------
# DESIGN SPACE SETUP --------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------


# Function which creates the appropriately sized blank design space
def generate_blank_gds(d_height=CHIP_HEIGHT,  # 3000
                       d_width=CHIP_WIDTH):  # 6000

    # Define a design bounding box as a visual guide
    outer_corners = [(0, 0), (d_width, 0), (d_width, d_height), (0, d_height)]
    polygon = Polygon(outer_corners)

    layout = GridLayout(title='Example_SOI_Devices_Zhaojin_2023',
                        frame_layer=CELL_OUTLINE_LAYER,
                        text_layer=LABEL_LAYER,
                        region_layer_type=None,
                        tight=True,
                        vertical_spacing=CELL_VERTICAL_SPACING,
                        vertical_alignment=1,
                        horizontal_spacing=CELL_HORIZONTAL_SPACING,
                        horizontal_alignment=10,#10
                        text_size=8 * LABEL_HEIGHT,# 2*LABEL_HEIGHT
                        row_text_size=15
                        )

    return layout, polygon


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# GENERIC DEVICE SWEEPS -----------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

# Roshan's comment

# Hi Hi Hi

########################
# GRATING LOOPBACK SWEEP
########################

def grating_sweep(layout_cell,current_width):

    # Grating Coupler sweep parameters:
    waveguide_widths = [WAVEGUIDE_WIDTH]
    added_waveguide_lengths = [10, 110, 210,150,100,80,160,200,140,101, 111, 211,151,81,161,201,141]
    periods = [GRATING_PERIOD_STANDARD]  # Periods to be swept over
    fill_factors = [GRATING_FILL_FACTOR_STANDARD]  # Fill-factors to be swept over
    cell_width = 0
    # current_width = 0

    # For each period and each fill-factor create a grating loop back and add to the loopback row
    for i, added_waveguide_length in enumerate(added_waveguide_lengths):
        for j, waveguide_width in enumerate(waveguide_widths):
            for k, period in enumerate(periods):
                for m, fill_factor in enumerate(fill_factors):
                    sweep_coupler_params = {
                        'width': waveguide_width,
                        'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
                        'grating_period': GRATING_PERIOD_STANDARD,
                        'grating_ff': fill_factor,
                        'n_gratings': GRATING_NO_PERIODS,
                        'taper_length': GRATING_TAPER_LENGTH
                    }
                    # temp_cell = grating_loopback(sweep_coupler_params,
                    #                              taper_route=added_waveguide_length,
                    #                              name='Grating Loopback\nAdded Length {0}um\nWidth {1}um\nPeriod {2}um\nff {3}'.format(added_waveguide_length, waveguide_width, round(period, 3), fill_factor)
                    #                              )

                    # cell_width = -temp_cell.bounds[0] + temp_cell.bounds[2]
                    # current_width = current_width + cell_width + layout_cell.horizontal_spacing * 2  # 1.5

                    sweep_grating_loopback = grating_loopback(sweep_coupler_params,
                                                 taper_route=added_waveguide_length,
                                                 name='Grating Loopback_ZL\nAdded Length {0}um\nWidth {1}um\nPeriod {2}um\nff {3}'.format(added_waveguide_length, waveguide_width, round(period, 3), fill_factor)
                                                 )

                    cell_width = -sweep_grating_loopback.bounds[0] + sweep_grating_loopback.bounds[2]

                    current_width = current_width + cell_width + layout_cell.horizontal_spacing*1.5

                    # Add to row if it will fit
                    # if current_width > CHIP_WIDTH:
                    #     layout_cell.begin_new_row()
                    #     layout_cell.add_to_row(temp_cell)
                    #     current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
                    # else:
                    #     layout_cell.add_to_row(temp_cell)

                    if current_width > CHIP_WIDTH:
                        layout_cell.begin_new_row()
                        layout_cell.add_to_row(sweep_grating_loopback)
                        current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
                    else:
                        layout_cell.add_to_row(sweep_grating_loopback)



    return layout_cell, current_width


#################
# TEST STRUCTURES
#################

def test_structure_gc(layout_cell):

    temp_cell = grating_loopback(coupler_params,
                                 taper_route=GRATING_TAPER_ROUTE,
                                 name='TEST Grating Loopback\nPeriod {0}um  ff {1}\nGrating Taper Length {2}um'.format(GRATING_PERIOD_STANDARD, GRATING_FILL_FACTOR_STANDARD, GRATING_TAPER_LENGTH))

    # cell_width = -temp_cell.bounds[0] + temp_cell.bounds[2]
    # current_width = current_width + cell_width + layout_cell.horizontal_spacing * 2  # 1.5
    # if current_width > CHIP_WIDTH:
    #     layout_cell.begin_new_row()
    #     layout_cell.add_to_row(temp_cell)
    #     current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
    # else:
    #     layout_cell.add_to_row(temp_cell)

    layout_cell.add_to_row(temp_cell)

    return layout_cell# , current_width



#####################
# DIRECTIONAL COUPLER
#####################

def directional_coupler_sweep(layout_cell, current_width):

    gaps = [0.25]
    coupling_lengths = [1.27]
    coupling_ratios = ['90 : 10']   # For naming purposes

    for i, gap in enumerate(gaps):
        for j, coupling_length in enumerate(coupling_lengths):

            temp_cell = directional_coupler(coupler_params,
                                            coupling_length=coupling_length,
                                            gap=gap,
                                            name='Directional Coupler  {0}\nGap {1}um\nCoupling Length {2}um'.format(coupling_ratios[j], gap, coupling_length))

            cell_width = -temp_cell.bounds[0] + temp_cell.bounds[2]
            current_width = current_width + cell_width + layout_cell.horizontal_spacing * 2  # 1.5
            if current_width > CHIP_WIDTH:
                layout_cell.begin_new_row()
                layout_cell.add_to_row(temp_cell)
                current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
            else:
                layout_cell.add_to_row(temp_cell)

            layout_cell.add_to_row(temp_cell)

    return layout_cell  , current_width


#########
# 1x2 MMI
#########

def mmi_1X2_sweep(layout_cell):

    mmi_length = 32.7
    mmi_width = 6
    mmi_taper_width = 1.5
    mmi_taper_length = 20

    temp_cell = mmi_1x2(coupler_params,
                        mmi_length=mmi_length,
                        mmi_width=mmi_width,
                        mmi_taper_width=mmi_taper_width,
                        mmi_taper_length=mmi_taper_length,
                        name='1x2 MMI')

    # cell_width = -temp_cell.bounds[0] + temp_cell.bounds[2]
    # current_width = current_width + cell_width + layout_cell.horizontal_spacing * 2  # 1.5
    # if current_width > CHIP_WIDTH:
    #     layout_cell.begin_new_row()
    #     layout_cell.add_to_row(temp_cell)
    #     current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
    # else:
    #     layout_cell.add_to_row(temp_cell)

    layout_cell.add_to_row(temp_cell)

    return layout_cell# , current_width


#########
# 2x2 MMI
#########

def mmi_2X2_sweep(layout_cell):

    mmi_length = 44.8
    mmi_width = 6
    mmi_taper_width = 1.5
    mmi_taper_length = 20

    temp_cell = mmi_2x2(coupler_params,
                        mmi_length=mmi_length,
                        mmi_width=mmi_width,
                        mmi_taper_width=mmi_taper_width,
                        mmi_taper_length=mmi_taper_length,
                        name='2x2 MMI')

    # cell_width = -temp_cell.bounds[0] + temp_cell.bounds[2]
    # current_width = current_width + cell_width + layout_cell.horizontal_spacing * 2  # 1.5
    # if current_width > CHIP_WIDTH:
    #     layout_cell.begin_new_row()
    #     layout_cell.add_to_row(temp_cell)
    #     current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
    # else:
    #     layout_cell.add_to_row(temp_cell)

    layout_cell.add_to_row(temp_cell)

    return layout_cell# , current_width


######################
# RING RESONATOR SWEEP
######################

def ring_sweep(layout_cell,current_width):

    ring_radii = np.linspace(70, 120, 3)    # Ring radii to be swept over (start, stop, no. steps)
    gap_size = np.linspace(0.250, 0.750, 3) # Gap sizes to be swept over (start, stop, no. steps)

    for i, ring_radius in enumerate(ring_radii):
        for j, gap in enumerate(gap_size):
            sweep_ring_parameters = coupler_params
            sweep_ring_resonator = ring_resonator(sweep_ring_parameters,
                                                  gap=gap,
                                                  radius=ring_radius,
                                                  name='Ring_Resonator_ZL\nRadius_' + str(ring_radius) + '\nGap_' + str(gap))
            # layout_cell.add_to_row(sweep_ring_resonator)

            cell_width = -sweep_ring_resonator.bounds[0] + sweep_ring_resonator.bounds[2]

            current_width = current_width + cell_width + layout_cell.horizontal_spacing * 1.5

            # Add to row if it will fit
            # if current_width > CHIP_WIDTH:
            #     layout_cell.begin_new_row()
            #     layout_cell.add_to_row(temp_cell)
            #     current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
            # else:
            #     layout_cell.add_to_row(temp_cell)

            if current_width > CHIP_WIDTH:
                layout_cell.begin_new_row()
                layout_cell.add_to_row(sweep_ring_resonator)
                current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
            else:
                layout_cell.add_to_row(sweep_ring_resonator)

    return layout_cell, current_width


##############
# SPIRAL SWEEP
##############

def spiral_sweep(layout_cell,current_width):

    # Sweep parameters:
    number_of_loops = [17, 22, 28]
    gap_sizes = [10]
    inner_gap_sizes = [15]

    # for each parameter
    for i, loop_numbers in enumerate(number_of_loops):
        for j, gap_size in enumerate(gap_sizes):
            for k, inner_gap_size in enumerate(inner_gap_sizes):
                sweep_spiral = spiral_loopback(coupler_params,
                                               name='SB_Spiral\nNo._loops_' + str(loop_numbers) + '\nGap_between_waveguides_' + str(gap_size) + '\nInner_circle_radius_' + str(inner_gap_size),
                                               number=loop_numbers,
                                               gap_size=gap_size,
                                               inner_gap_size=inner_gap_size
                                               )

                # layout_cell.add_to_row(sweep_spiral)
                cell_width = -sweep_spiral.bounds[0] + sweep_spiral.bounds[2]

                current_width = current_width + cell_width + layout_cell.horizontal_spacing * 1.5

                # Add to row if it will fit
                # if current_width > CHIP_WIDTH:
                #     layout_cell.begin_new_row()
                #     layout_cell.add_to_row(temp_cell)
                #     current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
                # else:
                #     layout_cell.add_to_row(temp_cell)

                if current_width > CHIP_WIDTH:
                    layout_cell.begin_new_row()
                    layout_cell.add_to_row(sweep_spiral)
                    current_width = cell_width + layout_cell.horizontal_alignment + layout_cell.horizontal_spacing
                else:
                    layout_cell.add_to_row(sweep_spiral)





    return layout_cell, current_width



# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# DESIGN SPACE LAYOUT -------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

def populate_gds(layout_cell, polygon):

    current_width = layout_cell.horizontal_alignment

    layout_cell.begin_new_row()

    #layout_cell, current_width = grating_sweep(layout_cell, current_width)

    # Add the device sweeps to the layout cell
    # layout_cell = test_structure_gc(layout_cell)
 # test change

    # layout_cell = mmi_1X2_sweep(layout_cell)
    # layout_cell = mmi_2X2_sweep(layout_cell)
    # layout_cell, current_width = directional_coupler_sweep(layout_cell, current_width)
    layout_cell, current_width = spiral_sweep(layout_cell,current_width)
    layout_cell.begin_new_row()
    layout_cell,current_width = ring_sweep(layout_cell,current_width)
    layout_cell.begin_new_row()
    layout_cell, current_width = grating_sweep(layout_cell, current_width)
    # Generate the design space populated with the devices
    design_space_cell, mapping = layout_cell.generate_layout(cell_name='Cell0_University_of_Bristol_Nanofab_2024_ZL')

    # Add our bounding box
    design_space_cell.add_to_layer(CELL_OUTLINE_LAYER, polygon)

    # Save our GDS
    design_space_cell.save('{0}SOI_Devices_ZL_2023.gds'.format(savepath))
    # design_space_cell.show()

    return design_space_cell


# Call the function which generates a blank design space
blank_design_space, bounding_box = generate_blank_gds()

# Populate the blank gds with all of our devices
populate_gds(blank_design_space, bounding_box)