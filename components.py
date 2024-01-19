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

