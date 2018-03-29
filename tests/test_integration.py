"""
This unit test checks numerical integration functions from integrate.py with TrajectoryGenerator.

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

from unittest import TestCase

from TrajectoryGenerator import Trajectory
from src.integrate import simps_integrate, quad_integrate, trapz_integrate


def integrate_and_test(method):
    """ Integrate trajectory accelerations and return errors compared to analytical trajectory

    :param method: callable ``f(times, vectors, start)``
        integration method to integrate vectors over times
    :return 1xn numpy array of absolute errors
    """
    integrated_trajectory = get_integrated_trajectory(method)
    # check integrated trajectory
    error = Trajectory().check_trajectory(integrated_trajectory)
    return error


def get_integrated_trajectory(method):
    """ Return TrajectoryGenerator trajectory integrated with given methods

    :param method callable ``f(times, vectors, start)``
        integration method to integrate vectors over times
    """

    # create trajectory
    trajectory = Trajectory()
    # get motion timestamps
    times = trajectory.get_times()
    start_position = trajectory.get_start_position()
    start_velocity = trajectory.get_start_velocity()
    # get analytical accelerations
    accelerations = trajectory.get_analytical_accelerations()
    # numerical integrate acceleration to get velocities
    velocities = method(times, accelerations, start_velocity)
    # numerical integrate velocities to get trajectory
    integrated_trajectory = method(times, velocities, start_position)
    return integrated_trajectory


class IntegrationTest(TestCase):

    def test_trajectory_generator(self):
        error = integrate_and_test(simps_integrate)
        self.assertLess(error.mean(), 0.05)

    def test_simple_integrate(self):
        """ Simple integration methods test with trigonometry functions"""

        # TODO remove when trajectory will be generalized
        import numpy as np
        from scipy import sin, cos
        times = np.arange(start=0, stop=100, step=1e-2)
        sinus = np.array([sin(x) for x in times])
        cosines = np.array([cos(x) for x in times])
        vector = np.vstack((sinus, cosines, -sinus))
        # for each integration method
        for method in [quad_integrate, trapz_integrate, simps_integrate]:
            # numerical integrate with selected method
            integrated = method(times, vector, initial=[-1, 0, 1])
            # calculate absolute error
            error = abs(np.array(
                [integrated[0] - (-cosines),
                 integrated[1] - sinus,
                 integrated[2] - cosines]
            ))
            # check error is below a threshold
            self.assertTrue(error.mean() < 0.005)