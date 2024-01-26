import numpy as np
from math import pi

import shapely.geometry.multipolygon
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.coupler import GratingCoupler
from gdshelpers.parts.port import Port
from gdshelpers.parts.spiral import Spiral
from gdshelpers.parts.splitter import MMI
from gdshelpers.parts.resonator import RingResonator
from gdshelpers.parts.splitter import DirectionalCoupler
from gdshelpers.parts.text import Text
from gdshelpers.parts.image import GdsImage
from shapely.geometry import Polygon, Point
from gdshelpers.geometry.shapely_adapter import geometric_union

from parameters import *

# ---------------------------------------------------------------------------------------------------------------------
# GRATING COUPLER -----------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

############################
# GRATING COUPLER DEFINITION
############################

# Do not delete or change!
CORNERSTONE_GRATING_IDENTIFIER = 0


# Class for linear grating coupler design compliant with Cornerstone fab
class CornerstoneGratingCoupler:

    def __init__(self):

        self.coupler_params = None
        self.origin = None
        self.port = None
        self.cell = None
        self.object = None

    # Function to create the Cornerstone compliant grating cell
    def create_coupler(self, origin, coupler_params, grating_angle=-np.pi/2):  # , name=None):
        gc_proto = GratingCoupler.make_traditional_coupler(origin=origin,
                                                           extra_triangle_layer=False,
                                                           **coupler_params)
        gc_proto_shape_obj = gc_proto.get_shapely_object()
        gc_outline = gc_proto_shape_obj.convex_hull
        coupler_params_modified = {
            'width': coupler_params['width'],
            'full_opening_angle': coupler_params['full_opening_angle'] + np.deg2rad(0.35),
            'grating_period': coupler_params['grating_period'],
            'grating_ff': coupler_params['grating_ff'],
            'n_gratings': coupler_params['n_gratings'],
            'taper_length': coupler_params['taper_length']
        }

        gc_teeth = GratingCoupler.make_traditional_coupler(origin=origin,
                                                           extra_triangle_layer=True,
                                                           angle=grating_angle,
                                                           # **teeth_coupler_params)
                                                            **coupler_params_modified)

        global CORNERSTONE_GRATING_IDENTIFIER
        cell = Cell("GC_period_{}_coords_{}_{}_{}".format(coupler_params['grating_period'],
                                                          origin[0],
                                                          origin[1], CORNERSTONE_GRATING_IDENTIFIER))
        CORNERSTONE_GRATING_IDENTIFIER += 1

        # Add outline to draw layer
        cell.add_to_layer(WAVEGUIDE_LAYER, gc_outline)
        cell.add_to_layer(GRATING_LAYER, gc_teeth)

        self.cell = cell
        self.port = gc_proto.port
        self.object = gc_proto_shape_obj

        return self

    @classmethod    # Function to make a grating coupler at a port
    def create_cornerstone_coupler_at_port(self, port, angle, **kwargs):

        if 'width' not in kwargs:
            kwargs['width'] = port.width

        if 'angle' not in kwargs:
            kwargs['angle'] = port.angle

        coup_params = kwargs

        return self.create_coupler(self,
                                   origin=port.origin,
                                   coupler_params=coup_params,
                                   grating_angle=angle)


# Utility function which checks that grating couplers are appropriately placed
def grating_checker(gratings):

    y_diff = np.around(gratings[0].port.origin[1], 9) - np.around(gratings[1].port.origin[1], 9)
    x_diff = np.around(gratings[0].port.origin[0], 9) - np.around(gratings[1].port.origin[0], 9)

    if y_diff != 0:
        print(" \n \n WARNING: The gratings being checked have a y separation of {}  \n \n ".format(y_diff))
    if np.abs(x_diff) % (GRATING_PITCH) != 0:
        print(" \n \n WARNING: The gratings being checked have a x separation of {}. Recommended is {}, {}, {}, {}... \n \n "
              .format(np.abs(x_diff), GRATING_PITCH, 2*GRATING_PITCH, 3*GRATING_PITCH, 4*GRATING_PITCH))
    # elif np.abs(x_diff) == (GRATING_PITCH/2):
    #     print(" \n \n WARNING: The gratings being checked have a x separation of {}. Recommended is {}, {}, {}, {}... \n \n "
    #           .format(np.abs(x_diff), GRATING_PITCH, 2* GRATING_PITCH, 3* GRATING_PITCH, 4* GRATING_PITCH))

    return x_diff, y_diff


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# DEVICE DEFINITIONS --------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------------------
# STANDARD DEVICES ----------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

##################
# GRATING LOOPBACK
##################

def grating_loopback(coupler_params,
                     taper_route,
                     position=(0, 0),
                     name='GRATING_LOOPBACK'):

    # Create the cell that we are going to add to
    grating_loopback_cell = Cell(name)
    grating_loopback_cell.add_to_layer(LABEL_LAYER,
                                       Text(origin=LABEL_ORIGIN,
                                            height=10,#LABEL_HEIGHT,
                                            angle=LABEL_ANGLE_VERTICAL,
                                            text=name
                                            )
                                       )

    # Create the left hand side grating
    left_grating = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    # Join our grating couplers together
    wg = Waveguide.make_at_port(port=left_grating.port)         # Create waveguide at the left grating port location
    wg.add_straight_segment(length=taper_route)                 # Routing from taper to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)              # Add the left-hand bend
    wg.add_straight_segment(length=GRATING_PITCH - 2 * BEND_RADIUS)  # Routing from bend to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)              # Add the right-hand bend
    wg.add_straight_segment(length=taper_route)                 # Routing from bend to taper

    # Create the right grating coupler at the waveguide port location
    right_grating = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg.current_port,
        **coupler_params, angle=wg.angle)

    # Add the left grating coupler cell to our loopback cell
    grating_loopback_cell.add_cell(left_grating.cell)  # Add the left grating coupler cell to our loopback cell
    grating_loopback_cell.add_cell(right_grating.cell)  # Add the right grating to the loopback cell
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg)  # Add the waveguide to the loopback cell

    # Grating checker
    grating_checker([left_grating, right_grating])

    return grating_loopback_cell


#####################
# DIRECTIONAL COUPLER
#####################

def directional_coupler(coupler_params,
                        coupling_length,
                        gap,
                        position=(0, 0),
                        name='DIRECTIONAL_COUPLER'):

    # Create the cell that we are going to add to
    directional_coupler_cell = Cell(name)
    directional_coupler_cell.add_to_layer(LABEL_LAYER,
                                          Text(origin=LABEL_ORIGIN,
                                               height=LABEL_HEIGHT,
                                               angle=LABEL_ANGLE_VERTICAL,
                                               text=name
                                               )
                                          )

    # Create the first left-hand side grating coupler
    left_grating1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    # Create the second left-hand side grating coupler
    left_grating2 = CornerstoneGratingCoupler().create_coupler(
        origin=(GRATING_PITCH, position[1]),
        coupler_params=coupler_params)

    # Route the second left-hand grating coupler to the DC
    wg2 = Waveguide.make_at_port(port=left_grating2.port)  # Create waveguide at the port location of the second grating coupler
    wg2.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from taper to bend
    wg2.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the left-hand bend
    wg2.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from bend to bottom left DC input

    # Create a DC at the waveguide attached to the second left-hand grating coupler
    DC = DirectionalCoupler.make_at_port(port=wg2.current_port,
                                         length=coupling_length,
                                         gap=gap,
                                         bend_radius=BEND_RADIUS)

    # Route the first left-hand grating coupler to the DC
    wg1 = Waveguide.make_at_port(port=left_grating1.port)   # Create waveguide at the port location of the first grating coupler
    wg1.add_straight_segment_until_y(DC.left_ports[1].origin[1] - BEND_RADIUS)  # Routing from taper to bend
    wg1.add_bend(angle=-pi / 2, radius=BEND_RADIUS) # Add the left-hand bend
    wg1.add_straight_segment_until_x(DC.left_ports[1].origin[0])  # Routing from bend to top left DC input

    # Route the DC to the first right-hand grating coupler
    wg3 = Waveguide.make_at_port(port=DC.right_ports[0])  # Create waveguide at the bottom right DC output port
    wg3.add_straight_segment_until_x(2*GRATING_PITCH - BEND_RADIUS)  # Routing from bottom right DC output port to bend
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the right-hand bend
    wg3.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from bend to taper of first right-hand side grating coupler

    # Route the DC to the second right hand grating coupler
    wg4 = Waveguide.make_at_port(port=DC.right_ports[1])  # Create waveguide at the top right DC output port
    wg4.add_straight_segment_until_x(3*GRATING_PITCH - BEND_RADIUS)  # Routing from top right DC output port to bend
    wg4.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the right-hand bend
    wg4.add_straight_segment_until_y(wg3.current_port.origin[1])  # Routing from bend to taper of second right-hand side grating coupler

    # Create the first right-hand side grating coupler
    right_grating1 = CornerstoneGratingCoupler().create_coupler(
        origin=((2 * GRATING_PITCH), position[1]),
        coupler_params=coupler_params)

    # Create the first right-hand side grating coupler
    right_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg4.current_port,
        **coupler_params,
        angle=wg4.angle)

    # # Create the right grating coupler at the waveguide port location
    # right_grating = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     port=wg.current_port,
    #     **coupler_params, angle=wg.angle)


    # Add the sub-components to the respective cell and layers
    # directional_coupler_cell.add_cell(left_grating1.cell)  # Add the first left-hand grating coupler cell to the DC cell
    # directional_coupler_cell.add_cell(left_grating2.cell)  # Add the second left-hand grating coupler cell to the DC cell
    # directional_coupler_cell.add_to_layer(WAVEGUIDE_LAYER, wg1)  # Add the first waveguide to the loopback cell
    # directional_coupler_cell.add_to_layer(WAVEGUIDE_LAYER, wg2)  # Add the second waveguide to the loopback cell
    directional_coupler_cell.add_to_layer(WAVEGUIDE_LAYER, DC)  # Add the DC sub-component to the DC cell
    # directional_coupler_cell.add_to_layer(WAVEGUIDE_LAYER, wg3)  # Add the third waveguide to the DC cell
    # directional_coupler_cell.add_to_layer(WAVEGUIDE_LAYER, wg4)  # Add the fourth waveguide to the DC cell
    # directional_coupler_cell.add_cell(right_grating1.cell)  # Add the first right-hand grating coupler to the DC cell
    # directional_coupler_cell.add_cell(right_grating2.cell)  # Add the second right-hand grating coupler to the DC cell

    # Grating checker
    grating_checker([left_grating1, left_grating2])
    grating_checker([left_grating1, right_grating1])
    grating_checker([left_grating1, right_grating2])

    return directional_coupler_cell


#########
# MMI 1X2
#########

def mmi_1x2(coupler_params,
            mmi_length,
            mmi_width,
            mmi_taper_width,
            mmi_taper_length,
            position=(0, 0),
            name='MMI_1X2'):

    # Create the cell that we are going to add to
    mmi_1x2_cell = Cell(name)
    mmi_1x2_cell.add_to_layer(LABEL_LAYER,
                              Text(origin=LABEL_ORIGIN,
                                   height=LABEL_HEIGHT,
                                   angle=LABEL_ANGLE_VERTICAL,
                                   text=name
                                   )
                              )

    # Create the left hand side grating coupler
    left_grating = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    # Route the left-hand grating coupler to the MMI input port
    wg = Waveguide.make_at_port(port=left_grating.port) # Create a waveguide at the left-hand grating coupler port location
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE) # Routing from taper to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the left-hand bend
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE) # Add a straight section of waveguide

    # Create a 1x2 MMI at the waveguide attached to the left-hand grating coupler
    mmi = MMI.make_at_port(port=wg.current_port,
                           length=mmi_length,
                           width=mmi_width,
                           num_inputs=1,
                           num_outputs=2,
                           taper_width=mmi_taper_width,
                           taper_length=mmi_taper_length)

    wg_position_buffer = Waveguide.make_at_port(port=left_grating.port) # Workaround: make a "waveguide" of 0 length at the left-hand grating coupler port

    # Route the MMI to the first right-hand grating coupler
    wg1 = Waveguide.make_at_port(port=mmi.output_ports[0])  # Create waveguide at the bottom right output of the MMI
    wg1.add_straight_segment_until_x(2*GRATING_PITCH - BEND_RADIUS) # Routing from bottom right MMI output to bend
    wg1.add_bend(angle=-pi/2, radius=BEND_RADIUS)   # Add the right-hand bend
    wg1.add_straight_segment_until_y(wg_position_buffer.origin[1])  # Routing from bend to top of first right-hand grating coupler taper

    # Route the MMI to the first right-hand grating coupler
    wg2 = Waveguide.make_at_port(port=mmi.output_ports[1])  # Create waveguide at the top right output of the MMI
    wg2.add_straight_segment_until_x(3 * GRATING_PITCH - BEND_RADIUS) # Routing from top right MMI output to bend
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)   # Add the right-hand bend
    wg2.add_straight_segment_until_y(wg_position_buffer.origin[1])  # Routing from bend to top of second right-hand grating coupler taper

    # Create the right grating couplers at the waveguide port locations
    right_grating1 = CornerstoneGratingCoupler().create_coupler(origin=((2 * GRATING_PITCH), position[1]), coupler_params=coupler_params)
    right_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg2.current_port, **coupler_params, angle=wg2.angle)

    # Add the sub-components to the respective cell and layers
    mmi_1x2_cell.add_cell(left_grating.cell)  # Add the left grating coupler cell to our MMI cell
    mmi_1x2_cell.add_cell(right_grating1.cell)  # Add the first right grating coupler to the MMI cell
    mmi_1x2_cell.add_cell(right_grating2.cell)  # Add the second right grating coupler to the MMI cell
    mmi_1x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg)  # Add the first waveguide to the MMI cell
    mmi_1x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg1)  # Add the second waveguide to the MMI cell
    mmi_1x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg2)  # Add the third waveguide to the MMI cell
    mmi_1x2_cell.add_to_layer(WAVEGUIDE_LAYER, mmi) # Add the MMI sub-component to the MMI cell

    # Grating checker
    grating_checker([left_grating, right_grating1])
    grating_checker([left_grating, right_grating2])

    return mmi_1x2_cell


#########
# MMI 2X2
#########

def mmi_2x2(coupler_params,
            mmi_length,
            mmi_width,
            mmi_taper_width,
            mmi_taper_length,
            position=(0, 0),
            name='MMI_2X2'):

    # Create the cell that we are going to add to
    mmi_2x2_cell = Cell(name)
    mmi_2x2_cell.add_to_layer(LABEL_LAYER,
                              Text(origin=LABEL_ORIGIN,
                                   height=LABEL_HEIGHT,
                                   angle=LABEL_ANGLE_VERTICAL,
                                   text=name
                                   )
                              )

    # Create the left hand side grating
    left_grating1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    left_grating2 = CornerstoneGratingCoupler().create_coupler(
        origin=(GRATING_PITCH, position[1]),
        coupler_params=coupler_params)

    # Route the first left-hand grating coupler to the MMI bottom input port
    wg = Waveguide.make_at_port(port=left_grating1.port)         # Create waveguide at the left grating port location
    wg.add_straight_segment(length=2*GRATING_TAPER_ROUTE)                 # Routing from taper to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)              # Add the left-hand bend
    wg.add_straight_segment(length=GRATING_PITCH + GRATING_TAPER_ROUTE)

    mmi = MMI.make_at_port(port=wg.current_port, length=mmi_length, width=mmi_width, num_inputs=2, num_outputs=2, taper_width=mmi_taper_width, taper_length=mmi_taper_length, pos='i0')

    wg_position_buffer = Waveguide.make_at_port(port=left_grating1.port)
    wg_position_buffer2 = Waveguide.make_at_port(port=left_grating2.port)

    wg4 = Waveguide.make_at_port(port=mmi.input_ports[0])  # Create waveguide at the left grating port location
    wg4.add_straight_segment_until_x(1*wg_position_buffer2.origin[0] + BEND_RADIUS)  # Routing from taper to bend
    wg4.add_bend(angle=pi / 2, radius=BEND_RADIUS)  # Add the left-hand bend
    wg4.add_straight_segment_until_y(wg_position_buffer2.origin[1])

    wg1 = Waveguide.make_at_port(port=mmi.output_ports[0])  # Create waveguide at the left grating port location
    wg1.add_straight_segment_until_x(3*GRATING_PITCH - BEND_RADIUS)
    wg1.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg1.add_straight_segment_until_y(wg_position_buffer.origin[1])

    wg2 = Waveguide.make_at_port(port=mmi.output_ports[1])
    wg2.add_straight_segment_until_x(4*GRATING_PITCH - BEND_RADIUS)
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment_until_y(wg_position_buffer.origin[1])

    # Create the right grating coupler at the waveguide port location
    right_grating1 = CornerstoneGratingCoupler().create_coupler(origin=((3 * GRATING_PITCH), position[1]), coupler_params=coupler_params)
    right_grating2 = CornerstoneGratingCoupler().create_coupler(origin=((4 * GRATING_PITCH), position[1]), coupler_params=coupler_params)


    # Add the sub-components to the respective cell and layers
    mmi_2x2_cell.add_cell(left_grating1.cell)  # Add the first left grating coupler cell to our MMI cell
    mmi_2x2_cell.add_cell(left_grating2.cell)  # Add the second left grating coupler cell to our MMI cell
    mmi_2x2_cell.add_cell(right_grating1.cell)  # Add the first right grating to the MMI cell
    mmi_2x2_cell.add_cell(right_grating2.cell)  # Add the second right grating to the MMI cell
    mmi_2x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg)  # Add the first waveguide to the MMI cell
    mmi_2x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg1)  # Add the second waveguide to the MMI cell
    mmi_2x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg2)  # Add the third waveguide to the MMI cell
    mmi_2x2_cell.add_to_layer(WAVEGUIDE_LAYER, wg4)  # Add the fourth waveguide to the MMI cell
    mmi_2x2_cell.add_to_layer(WAVEGUIDE_LAYER, mmi)  # Add the MMI sub-component to the MMI cell

    # Grating checker
    grating_checker([left_grating1, left_grating2])
    grating_checker([left_grating1, right_grating1])
    grating_checker([left_grating1, right_grating2])

    return mmi_2x2_cell


################
# RING RESONATOR
################

def ring_resonator(coupler_params,
                   gap,
                   radius,
                   position=(0, 0),
                   name='RING_RESONATOR'):

    # Create the cell that we are going to add to
    ring_resonator_cell = Cell(name)
    ring_resonator_cell.add_to_layer(LABEL_LAYER,
                                     Text(origin=LABEL_ORIGIN,
                                          height=LABEL_HEIGHT,
                                          angle=LABEL_ANGLE_VERTICAL,
                                          text=name
                                          )
                                     )

    # Create the left hand side grating
    left_grating = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    # Join our grating couplers together
    wg = Waveguide.make_at_port(port=left_grating.port)         # Create waveguide at the left grating port location
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)         # Routing from taper to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)              # Add the left-hand bend
    wg.add_straight_segment(length=(GRATING_PITCH - 2 * BEND_RADIUS) / 2)  # Add a waveguide to centre of top section
    resonator = RingResonator.make_at_port(wg.current_port, gap=gap, radius=radius)  # Add the ring
    wg.add_straight_segment(length=(GRATING_PITCH - 2 * BEND_RADIUS) / 2)  # Add the other half of the top waveguide
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)              # Add the right-hand bend
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)         # Routing from bend to taper

    # Create the right grating coupler at the waveguide port location
    right_grating = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg.current_port, **coupler_params, angle=wg.angle)

    # Add the left grating coupler cell to our loopback cell
    ring_resonator_cell.add_cell(left_grating.cell)  # Add the left grating coupler cell to our loopback cell
    ring_resonator_cell.add_cell(right_grating.cell)  # Add the right grating to the loopback cell
    ring_resonator_cell.add_to_layer(WAVEGUIDE_LAYER, wg)  # Add the waveguide to the loopback cell
    ring_resonator_cell.add_to_layer(WAVEGUIDE_LAYER, resonator)  # Add the waveguide to the loopback cell

    # Grating checker
    grating_checker([left_grating, right_grating])

    return ring_resonator_cell


#################
# SPIRAL WINDINGS
#################

def spiral_loopback(coupler_params,
                    number,
                    gap_size,
                    inner_gap_size,
                    position=(0, 0),
                    name='SPIRAL'):
    # Create the cell that we are going to add to
    spiral_loopback_cell = Cell(name)
    spiral_loopback_cell.add_to_layer(LABEL_LAYER,
                                      Text(origin=[150, -385],
                                           height=LABEL_HEIGHT,
                                           angle=LABEL_ANGLE_VERTICAL,
                                           text=name
                                           )
                                      )

    # Create the left hand side grating
    left_grating = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    # Join our grating couplers together
    wg = Waveguide.make_at_port(port=left_grating.port)  # Create waveguide at the left grating port location
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from taper to bend
    wg.add_bend(angle=pi/2, radius=BEND_RADIUS)

    spiral = Spiral.make_at_port(port=wg.current_port, num=number, gap=gap_size, inner_gap=inner_gap_size)
    spiral_length = spiral.length
    #print(spiral_length)
    spiral_obj = spiral.get_shapely_object()    # Generate a Shapely object for the spiral to find its bounding box coordinates
    spiral_size = abs(spiral_obj.bounds[1] - spiral_obj.bounds[3])  # Determine the size of the spiral

    wg2 = Waveguide.make_at_port(port=spiral.out_port)  # Create waveguide at the spiral output port location
    wg2.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from spiral to bend
    wg2.add_bend(angle=-pi, radius=BEND_RADIUS)  # Add the right-hand bend

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):   # VGA_NUM_CHANNELS = No. channels (fibres) in the VGA, pitched 127um = 8
        if (spiral_size/2) < j * GRATING_PITCH: # (spiral_size/2) because the spiral is centred above the GC
            wg2.add_straight_segment(length=j*GRATING_PITCH + GRATING_TAPER_ROUTE)  # Add straight waveguide to fit VGA pitch
            break

    wg2.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the right-hand bend
    wg2.add_straight_segment(length=GRATING_TAPER_ROUTE + spiral_size + 2*BEND_RADIUS - WAVEGUIDE_WIDTH)  # Routing from bend to taper

    # Create the right grating coupler at the waveguide port location
    right_grating = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg2.current_port, **coupler_params, angle=wg2.angle)

    # Add the left grating coupler cell to our loopback cell
    spiral_loopback_cell.add_cell(left_grating.cell)  # Add the left grating coupler cell to our loopback cell
    spiral_loopback_cell.add_cell(right_grating.cell)  # Add the right grating to the loopback cell
    spiral_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg)  # Add the waveguide to the loopback cell
    spiral_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg2)  # Add the waveguide to the loopback cell
    spiral_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, spiral)  # Add the spiral sub-component to the loopback cell

    # Grating checker
    grating_checker([left_grating, right_grating])

    return spiral_loopback_cell

def mzi_dc(coupler_params,
           coupling_length,
           gap,
           mzi_centre_spacing,
           path_length_difference,
           position=(0,0),
           name= 'MZI'):
    mzi_dc_cell = Cell(name)
    mzi_dc_cell.add_to_layer(LABEL_LAYER,
                             Text(origin = LABEL_ORIGIN,
                                  height = LABEL_HEIGHT,
                                  angle = LABEL_ANGLE_VERTICAL,
                                  text = name))

   # Create the left hand side grating coupler
    left_grating = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0],position[1]),
        coupler_params=coupler_params
    )

    # Create the Straight Waveguide and bend
    wg1 = Waveguide.make_at_port(
        port=left_grating.port)  # Create waveguide at the port location of the second grating coupler
    wg1.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from taper to bend
    wg1.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the left-hand bend
    wg1.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from bend to bottom left DC input

    # Create the first DC
    DC1 = DirectionalCoupler.make_at_port(port=wg1.current_port,
                                         length=coupling_length,
                                         gap=gap,
                                         bend_radius=BEND_RADIUS)


    # Route the top MZI guide
    wg2 = Waveguide.make_at_port(port=DC1.right_ports[1])
    wg2.add_straight_segment(length=BEND_RADIUS)
    wg2.add_bend(angle=pi/2,radius=BEND_RADIUS)
    wg2.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    wg2.add_straight_segment(length=(mzi_centre_spacing-2*BEND_RADIUS))
    wg2.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    wg2.add_bend(angle= pi/2,radius=BEND_RADIUS)
    wg2.add_straight_segment(length=BEND_RADIUS)


    # Route the bottom MZI guide
    wg3 = Waveguide.make_at_port(port=DC1.right_ports[0])
    wg3.add_straight_segment(length=BEND_RADIUS)
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(mzi_centre_spacing - 2 * BEND_RADIUS))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=BEND_RADIUS)

    # Create the second DC
    DC2 = DirectionalCoupler.make_at_port(port=wg2.current_port,
                                          length=coupling_length,
                                          gap=gap,
                                          bend_radius=BEND_RADIUS,
                                          which=1)


    # Add a waveguide to the bottom output
    wg4 = Waveguide.make_at_port(port=DC2.right_ports[0])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
            if wg4.current_port.origin[0] < j * GRATING_PITCH:
                wg4.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
                break

    wg4.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    # wg4.add_straight_segment(length=GRATING_TAPER_ROUTE)

    wg4.add_straight_segment_until_y(left_grating.port.origin[1])

    right_grating1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg4.current_port,
                                                                                    **coupler_params,
                                                                                    angle=wg4.angle)


    # Add a waveguide to the top output
    wg5 = Waveguide.make_at_port(port=DC2.right_ports[1])
    wg5.add_straight_segment(GRATING_PITCH)

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
        if wg5.current_port.origin[0] < j * GRATING_PITCH:
            wg5.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
            break

    wg5.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg5.add_straight_segment_until_y(left_grating.port.origin[1])

    right_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg5.current_port,
                                                                                    **coupler_params,
                                                                                    angle=wg5.angle)

    # Add the sub-components to the MZI cell

    mzi_dc_cell.add_cell(left_grating.cell)
    mzi_dc_cell.add_cell(right_grating1.cell)
    mzi_dc_cell.add_cell(right_grating2.cell)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER,wg1)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER, wg2)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER, wg3)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER, wg4)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER, wg5)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER, DC1)
    mzi_dc_cell.add_to_layer(WAVEGUIDE_LAYER, DC2)

    # Grating checker
    grating_checker([left_grating,right_grating1])
    grating_checker([left_grating, right_grating2])

    return mzi_dc_cell



def mzi_dc2(coupler_params,
           coupling_length,
           gap,
           mzi_centre_spacing,
           path_length_difference,
           position=(0,0),
           name= 'MZI2'):
    mzi_dc2_cell = Cell(name)
    mzi_dc2_cell.add_to_layer(LABEL_LAYER,
                             Text(origin = LABEL_ORIGIN,
                                  height = LABEL_HEIGHT,
                                  angle = LABEL_ANGLE_VERTICAL,
                                  text = name))

   # Create the left hand side grating coupler
    left_grating1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0],position[1]),
        coupler_params=coupler_params
    )

    left_grating2 = CornerstoneGratingCoupler().create_coupler(
        origin=(GRATING_PITCH, position[1]),
        coupler_params=coupler_params)


    # Create the Straight Waveguide and bend
    wg = Waveguide.make_at_port(
        port=left_grating2.port)  # Create waveguide at the port location of the second grating coupler
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from taper to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS)  # Add the left-hand bend
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)  # Routing from bend to bottom left DC input

    # Create the first DC
    DC1 = DirectionalCoupler.make_at_port(port=wg.current_port,
                                         length=coupling_length,
                                         gap=gap,
                                         bend_radius=BEND_RADIUS)

    #Route the left grating 1 to the DC

    wg1 = Waveguide.make_at_port(port=left_grating1.port)
    wg1.add_straight_segment_until_y(DC1.left_ports[1].origin[1] - BEND_RADIUS)
    wg1.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg1.add_straight_segment_until_x(DC1.left_ports[1].origin[0])


    # Route the top MZI guide
    wg2 = Waveguide.make_at_port(port=DC1.right_ports[1])
    wg2.add_straight_segment(length=BEND_RADIUS)
    wg2.add_bend(angle=pi/2,radius=BEND_RADIUS)
    wg2.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    wg2.add_straight_segment(length=(mzi_centre_spacing-2*BEND_RADIUS))
    wg2.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    wg2.add_bend(angle= pi/2,radius=BEND_RADIUS)
    wg2.add_straight_segment(length=BEND_RADIUS)


    # Route the bottom MZI guide
    wg3 = Waveguide.make_at_port(port=DC1.right_ports[0])
    wg3.add_straight_segment(length=BEND_RADIUS)
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(mzi_centre_spacing - 2 * BEND_RADIUS))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=BEND_RADIUS)

    # Create the second DC
    DC2 = DirectionalCoupler.make_at_port(port=wg2.current_port,
                                          length=coupling_length,
                                          gap=gap,
                                          bend_radius=BEND_RADIUS,
                                          which=1)


    # Add a waveguide to the bottom output
    wg4 = Waveguide.make_at_port(port=DC2.right_ports[0])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
            if wg4.current_port.origin[0] < j * GRATING_PITCH:
                wg4.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
                break

    wg4.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    # wg4.add_straight_segment(length=GRATING_TAPER_ROUTE)

    wg4.add_straight_segment_until_y(left_grating1.port.origin[1])

    # right_grating1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg4.current_port,
    #                                                                                 **coupler_params,
    #                                                                                 angle=wg4.angle)
    right_grating1 = CornerstoneGratingCoupler().create_coupler(origin=(wg4.current_port.origin[0],position[1]),
                                                                coupler_params=coupler_params)

    # Add a waveguide to the top output
    wg5 = Waveguide.make_at_port(port=DC2.right_ports[1])
    wg5.add_straight_segment(GRATING_PITCH)

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
        if wg5.current_port.origin[0] < j * GRATING_PITCH:
            wg5.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
            break

    wg5.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg5.add_straight_segment_until_y(left_grating1.port.origin[1])

    right_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg5.current_port,
                                                                                    **coupler_params,
                                                                                    angle=wg5.angle)

    # Add the sub-components to the MZI cell

    mzi_dc2_cell.add_cell(left_grating1.cell)
    mzi_dc2_cell.add_cell(left_grating2.cell)
    mzi_dc2_cell.add_cell(right_grating1.cell)
    mzi_dc2_cell.add_cell(right_grating2.cell)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, wg)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER,wg1)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, wg2)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, wg3)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, wg4)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, wg5)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, DC1)
    mzi_dc2_cell.add_to_layer(WAVEGUIDE_LAYER, DC2)

    # Grating checker
    grating_checker([left_grating1,right_grating1])
    grating_checker([left_grating2, right_grating2])

    return mzi_dc2_cell

def cascaded_mzi_dc(coupler_params,
                    coupling_length,
                    gap,
                    mzi_center_spacing,
                    path_length_difference,
                    position=(0,0),
                    name='CASCADED_MZI'):
    cascaded_mzi = Cell(name)
    cascaded_mzi.add_to_layer(LABEL_LAYER,
                            Text(origin = LABEL_ORIGIN,
                                height = LABEL_HEIGHT,
                                angle = LABEL_ANGLE_VERTICAL,
                                text = name))

    # Create the left hand side grating coupler
    left_grating1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params
    )

    left_grating2 = CornerstoneGratingCoupler().create_coupler(
        origin = (GRATING_PITCH, position[1]),
        coupler_params=coupler_params
    )

    # Create the Straight Waveguide and bend
    wg = Waveguide.make_at_port(
        port=left_grating2.port) # Create waveguide at the port location of the second grating coupler
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE) # Routing from taper to bend
    wg.add_bend(angle=-pi / 2, radius=BEND_RADIUS) # Add the left-hand bend
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE) # Routing from bend to bottom left DC input

    # Create the first DC
    DC1 = DirectionalCoupler.make_at_port(port=wg.current_port,
                                        length=coupling_length,
                                        gap=gap,
                                        bend_radius=BEND_RADIUS)

    # Route the left grating 1 to the DC
    wg1 = Waveguide.make_at_port(port=left_grating1.port)
    wg1.add_straight_segment_until_y(DC1.left_ports[1].origin[1] - BEND_RADIUS)
    wg1.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg1.add_straight_segment_until_x(DC1.left_ports[1].origin[0])
    
    # Route the top MZI guide
    wg2 = Waveguide.make_at_port(port=DC1.right_ports[1])
    wg2.add_straight_segment(length=BEND_RADIUS)
    wg2.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment(length=(mzi_center_spacing - 2 * BEND_RADIUS))
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg2.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment(length=BEND_RADIUS)

    # Route the bottom MZI guide
    wg3 = Waveguide.make_at_port(port=DC1.right_ports[0])
    wg3.add_straight_segment(length=BEND_RADIUS)
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(mzi_center_spacing - 2 * BEND_RADIUS))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=BEND_RADIUS)

    # Create the second DC
    DC2 = DirectionalCoupler.make_at_port(port=wg2.current_port,
                                          length=coupling_length,
                                          gap=gap,
                                          bend_radius=BEND_RADIUS,
                                          which=1)


    # Add a waveguide to the bottom output
    wg4 = Waveguide.make_at_port(port=DC2.right_ports[0])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
            if wg4.current_port.origin[0] < j * GRATING_PITCH:
                wg4.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
                break

    wg4.add_bend(angle=-pi/2,radius=BEND_RADIUS)
    # wg4.add_straight_segment(length=GRATING_TAPER_ROUTE)

    wg4.add_straight_segment_until_y(left_grating1.port.origin[1])

    right_grating1 = CornerstoneGratingCoupler().create_coupler(origin=(wg4.current_port.origin[0],position[1]),
                                                                coupler_params=coupler_params)

    ##################

    # # Add a waveguide to the top output
    # wg5 = Waveguide.make_at_port(port=DC2.right_ports[1])
    # wg5.add_straight_segment(GRATING_PITCH)

    # # Routing to the next multiple of 127
    # for j in range(VGA_NUM_CHANNELS):
    #     if wg5.current_port.origin[0] < j * GRATING_PITCH:
    #         wg5.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
    #         break

    # wg5.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    # wg5.add_straight_segment_until_y(left_grating1.port.origin[1])

    # right_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(port=wg5.current_port,
    #                                                                                 **coupler_params,
    #                                                                                 angle=wg5.angle)
    

    # Add a waveguide to the top output
    wg5 = Waveguide.make_at_port(port=DC2.right_ports[1])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
        if wg5.current_port.origin[0] < j * GRATING_PITCH:
            wg5.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
            break
    
    wg5.add_bend(angle = pi / 2, radius = BEND_RADIUS)
    wg5.add_straight_segment(GRATING_PITCH)
    wg5.add_bend(angle= -pi / 2, radius = BEND_RADIUS)
    wg5.add_straight_segment(GRATING_PITCH)

    DC3 = DirectionalCoupler.make_at_port(port=wg5.current_port,
                                        length=coupling_length,
                                        gap=gap,
                                        bend_radius=BEND_RADIUS)

    # Top MZI guide
    wg6 = Waveguide.make_at_port(port=DC3.right_ports[1])
    wg6.add_straight_segment(length=BEND_RADIUS)
    wg6.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg6.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg6.add_straight_segment(length=(mzi_center_spacing-2*BEND_RADIUS))
    wg6.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg6.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg6.add_straight_segment(length=BEND_RADIUS)

    # Bottom MZI guide
    wg7 = Waveguide.make_at_port(port=DC3.right_ports[0])
    wg7.add_straight_segment(length=BEND_RADIUS)
    wg7.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg7.add_straight_segment(length=(path_length_difference/2))
    wg7.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg7.add_straight_segment(length=(mzi_center_spacing - 2 * BEND_RADIUS))
    wg7.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg7.add_straight_segment(length=(path_length_difference/2))
    wg7.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg7.add_straight_segment(length=BEND_RADIUS)

    # Create the DC
    DC4 = DirectionalCoupler.make_at_port(port=wg6.current_port,
                                        length=coupling_length,
                                        gap=gap,
                                        bend_radius=BEND_RADIUS,
                                        which=1)
    
    # 1st Cascaded MZI (top) 👆

    # 2nd Cascaded MZI (bottom) 👇

    # Add a waveguide to the bottom output
    wg8 = Waveguide.make_at_port(port=DC2.right_ports[0])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
        if wg8.current_port.origin[0] < j * GRATING_PITCH:
            wg8.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
            break
    
    wg8.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg8.add_straight_segment(GRATING_PITCH)
    wg8.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg8.add_straight_segment(GRATING_PITCH)

    # Create the DC
    DC5 = DirectionalCoupler.make_at_port(port=wg8.current_port,
                                        length=coupling_length,
                                        gap=gap,
                                        bend_radius=BEND_RADIUS,
                                        which=1)

    # Top MZI Guide
    wg9 = Waveguide.make_at_port(port=DC5.right_ports[1])
    wg9.add_straight_segment(length=BEND_RADIUS)
    wg9.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg9.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg9.add_straight_segment(length=(mzi_center_spacing-2*BEND_RADIUS))
    wg9.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg9.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg9.add_straight_segment(length=BEND_RADIUS)

    # Bottom MZI Guide
    wg10 = Waveguide.make_at_port(port=DC5.right_ports[0])
    wg10.add_straight_segment(length=BEND_RADIUS)
    wg10.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg10.add_straight_segment(length=(path_length_difference/2))
    wg10.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg10.add_straight_segment(length=(mzi_center_spacing - 2 * BEND_RADIUS))
    wg10.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg10.add_straight_segment(length=(path_length_difference/2))
    wg10.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg10.add_straight_segment(length=BEND_RADIUS)

    # Create the DC
    DC6 = DirectionalCoupler.make_at_port(port=wg9.current_port,
                                        length=coupling_length,
                                        gap=gap,
                                        bend_radius=BEND_RADIUS,
                                        which=1)
    

    #### TODO: Add Left Gratings for the Cascaded MZIs

    # wg11 = Waveguide.make_at_port(port=DC5.left_ports[0])

    # # # Routing to the next multiple of 127
    # # for j in range(VGA_NUM_CHANNELS):
    # #     if wg11.current_port.origin[0] < j * GRATING_PITCH:
    # #         wg11.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
    # #         break
    
    # wg11.add_bend(angle=pi/2, radius=BEND_RADIUS)



    # left_grating3 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     origin=()
    # )

    ################

    # Add the sub-components to the MZI cell

    cascaded_mzi.add_cell(left_grating1.cell)
    cascaded_mzi.add_cell(left_grating2.cell)
    # cascaded_mzi.add_cell(right_grating1.cell)
    # cascaded_mzi.add_cell(right_grating2.cell) #####
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER,wg1)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg2)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg3)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg4)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg5)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg6)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg7)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg8)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg9)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg10)
    # cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, wg11) 
    
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, DC1)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, DC2)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, DC3)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, DC4)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, DC5)
    cascaded_mzi.add_to_layer(WAVEGUIDE_LAYER, DC6)

    # Grating checker
    # grating_checker([left_grating1,right_grating1])
    # grating_checker([left_grating2, right_grating2]) ####
    # grating_checker([left_grating2, right_grating1])

    return cascaded_mzi

##############
# Final Device
##############

def custom_mzi(DC, 
                mzi_center_spacing, 
                path_length_difference
                ):
    # Route the top MZI guide
    wg2 = Waveguide.make_at_port(port=DC.right_ports[1])
    wg2.add_straight_segment(length=BEND_RADIUS)
    wg2.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment(length=(mzi_center_spacing - 2 * BEND_RADIUS))
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg2.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment(length=BEND_RADIUS)

    # Route the bottom MZI guide
    wg3 = Waveguide.make_at_port(port=DC.right_ports[0])
    wg3.add_straight_segment(length=BEND_RADIUS)
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(mzi_center_spacing - 2 * BEND_RADIUS))
    wg3.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=(path_length_difference/2))
    wg3.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg3.add_straight_segment(length=BEND_RADIUS)

    return wg2, wg3

def dc_mzi_block(cascaded_dc_mzi,
            coupler_params,
            wg,
            connection_port,
            coupling_length,
            gap,
            mzi_center_spacing,
            path_length_difference,
            connection_flag):

    # Create the First DC
    DC1 = DirectionalCoupler.make_at_port(port=wg.current_port,
                                        length=coupling_length,
                                        gap=gap,
                                        bend_radius=BEND_RADIUS)

    if connection_flag == 1:
        CONNECTION_PORT = connection_port.current_port
    else:
        CONNECTION_PORT = connection_port.port

    # Route the left grating 1 to the DC
    wg1 = Waveguide.make_at_port(port=CONNECTION_PORT)
    wg1.add_straight_segment_until_y(DC1.left_ports[1].origin[1] - BEND_RADIUS)
    wg1.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg1.add_straight_segment_until_x(DC1.left_ports[1].origin[0])

    top_mzi_1, bottom_mzi_1 = custom_mzi(
        DC1, 
        mzi_center_spacing, 
        path_length_difference
        )

    # Create the second DC
    DC2 = DirectionalCoupler.make_at_port(
        port=top_mzi_1.current_port,
        length=coupling_length,
        gap=gap,
        bend_radius=BEND_RADIUS,
        which=1
    )

    top_mzi_2, bottom_mzi_2 = custom_mzi(
        DC2,
        mzi_center_spacing,
        path_length_difference
    )

    DC3 = DirectionalCoupler.make_at_port(
        port=top_mzi_2.current_port,
        length=coupling_length,
        gap=gap,
        bend_radius=BEND_RADIUS,
        which=1
    )

    top_mzi_3, bottom_mzi_3 = custom_mzi(
        DC3,
        mzi_center_spacing,
        path_length_difference
    )

    DC4 = DirectionalCoupler.make_at_port(
        port=top_mzi_3.current_port,
        length=coupling_length,
        gap=gap,
        bend_radius=BEND_RADIUS,
        which=1
    )


    #### Add sub-components to the Waveguide Layer

    # Waveguides
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, wg1)

    # MZI 
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, top_mzi_1)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, bottom_mzi_1)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, top_mzi_2)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, bottom_mzi_2)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, top_mzi_3)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, bottom_mzi_3)

    # Directional Couplers
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, DC1)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, DC2)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, DC3)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, DC4)

    return DC4
    
    


def cascaded_straight_dc_mzi(coupler_params,
                            coupling_length,
                            gap,
                            mzi_center_spacing,
                            path_length_difference,
                            position=(0,0),
                            name='CASCADED_STRAIGHT_DC_MZI'):

    cascaded_dc_mzi = Cell(name)
    cascaded_dc_mzi.add_to_layer(LABEL_LAYER,
                                Text(origin = LABEL_ORIGIN,
                                height = LABEL_HEIGHT,
                                angle = LABEL_ANGLE_VERTICAL,
                                text = name))

    # Create the left hand side grating coupler
    left_grating1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params
    )

    left_grating2 = CornerstoneGratingCoupler().create_coupler(
        origin=(GRATING_PITCH, position[1]),
        coupler_params=coupler_params
    )


    # Create the Straight Waveguide and bend
    wg = Waveguide.make_at_port(
        port=left_grating2.port
    )
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)
    wg.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg.add_straight_segment(length=GRATING_TAPER_ROUTE)

    # DC-MZI Block

    DC_output = dc_mzi_block(
                    cascaded_dc_mzi,
                    coupler_params, 
                    wg, 
                    left_grating1, 
                    coupling_length, 
                    gap,
                    mzi_center_spacing,
                    path_length_difference,
                    connection_flag=0)
    
    wg1 = Waveguide.make_at_port(port=DC_output.right_ports[0])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
        if wg1.current_port.origin[0] < j * GRATING_PITCH:
            wg1.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
            break
    
    wg1.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg1.add_straight_segment(GRATING_PITCH)
    wg1.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg1.add_straight_segment(GRATING_PITCH)

    # # DC-MZI Block

    DC_bottom = DirectionalCoupler.make_at_port(
        port=wg1.current_port,
        length=coupling_length,
        gap=gap,
        bend_radius=BEND_RADIUS,
        which=1
    )

    # DC_output_2 = dc_mzi_block(
    #     cascaded_dc_mzi,
    #     coupler_params, 
    #     wg, 
    #     wg1, 
    #     coupling_length, 
    #     gap,
    #     mzi_center_spacing,
    #     path_length_difference,
    #     connection_flag=1
    # )

    wg2 = Waveguide.make_at_port(port=DC_output.right_ports[1])

    # Routing to the next multiple of 127
    for j in range(VGA_NUM_CHANNELS):
        if wg2.current_port.origin[0] < j * GRATING_PITCH:
            wg2.add_straight_segment_until_x(j * GRATING_PITCH - BEND_RADIUS)
            break
    
    wg2.add_bend(angle=pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment(GRATING_PITCH)
    wg2.add_bend(angle=-pi/2, radius=BEND_RADIUS)
    wg2.add_straight_segment(GRATING_PITCH)

    DC_top = DirectionalCoupler.make_at_port(
        port=wg2.current_port,
        length=coupling_length,
        gap=gap,
        bend_radius=BEND_RADIUS,
        which=1
    )

    #########

    # Add the sub-components to the MZI Cell
    cascaded_dc_mzi.add_cell(left_grating1.cell)
    cascaded_dc_mzi.add_cell(left_grating2.cell)

    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, wg)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, wg1)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, wg2)

    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, DC_top)
    cascaded_dc_mzi.add_to_layer(WAVEGUIDE_LAYER, DC_bottom)

    # Grating checker
    grating_checker([left_grating1, left_grating2])

    return cascaded_dc_mzi