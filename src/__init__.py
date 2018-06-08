"""
Entry point to src module functionalities.

This file is part of inertial_to_blender project,
a Blender simulation generator from inertial sensor data on cars.

Copyright (C) 2018  Federico Bertani
Author: Federico Bertani
Credits: Federico Bertani, Stefano Sinigardi, Alessandro Fabbri, Nico Curti

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


import numpy as np

from src.clean_data_utils import converts_measurement_units, reduce_disturbance, \
    clear_gyro_drift, correct_z_orientation, normalize_timestamp, \
    sign_inversion_is_necessary, get_stationary_times, correct_xy_orientation
from src.gnss_utils import get_positions, get_velocities, align_to_world, get_accelerations
from src.input_manager import parse_input, InputType
from src.integrate import simps_integrate, rotate_accelerations


def get_positions_times(path):
    """
    parse input file from path, clean data and integrate positions

    :param path: string input file
    :return: 2 numpy array: 3xn position, 1xn times
    """

    window_size = 20

    # currently default format is unmodified fullinertial but other formats are / will be supported
    times, coordinates, altitudes, gps_speed, accelerations, angular_velocities = parse_input(path, [
        InputType.UNMOD_FULLINERTIAL])

    converts_measurement_units(accelerations, angular_velocities, gps_speed, coordinates)

    # get positions from GNSS data
    gnss_positions, headings = get_positions(coordinates, altitudes)

    # reduce accelerations disturbance
    times, accelerations = reduce_disturbance(times, accelerations, window_size)
    # reduce angular velocities disturbance
    _, angular_velocities = reduce_disturbance(times, angular_velocities, window_size)
    # truncate other array to match length of acc, thetas, times array
    gnss_positions = gnss_positions[:, round(window_size / 2):-round(window_size / 2)]

    # with "final" times now get velocities and
    real_velocities = get_velocities(times, gnss_positions)
    # scalar speed from gnns position (better than from dataset because avoids Kalmar filter)
    real_speeds = np.linalg.norm(real_velocities, axis=0)

    # get time windows where vehicle is stationary
    stationary_times = get_stationary_times(real_speeds)

    # clear gyroscope drift
    angular_velocities = clear_gyro_drift(angular_velocities, stationary_times)
    # set times start to 0
    normalize_timestamp(times)

    # correct z-axis aligment
    accelerations, angular_velocities = correct_z_orientation(accelerations, angular_velocities, stationary_times)

    # remove g
    accelerations[2] -= accelerations[2, stationary_times[0][0]:stationary_times[0][-1]].mean()

    # correct alignment in xy plane
    accelerations = correct_xy_orientation(accelerations, angular_velocities)

    # convert to laboratory frame of reference
    accelerations = rotate_accelerations(times, accelerations, angular_velocities)

    # rotate to align y to north, x to east
    accelerations = align_to_world(gnss_positions, accelerations, stationary_times)


    initial_speed = np.array([[gps_speed[0]], [0], [0]])
    # integrate acceleration with gss velocities correction
    correct_velocities = simps_integrate(times, accelerations, initial_speed, adjust_data=real_velocities,
                                         adjust_frequency=1)

    if sign_inversion_is_necessary(correct_velocities):
        accelerations *= -1
        correct_velocities *= -1

    correct_position = simps_integrate(times, correct_velocities, adjust_data=gnss_positions, adjust_frequency=1)

    return correct_position, times