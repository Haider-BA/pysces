import numpy as np

class EuclideanTransformation(object):
    def __init__(self, angle, displacement):
        self.angle = angle
        self.displacement = displacement

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value
        th = value * np.pi / 180
        self._R = np.array([[np.cos(th), np.sin(th)],[-np.sin(th), np.cos(th)]])

    @property
    def displacement(self):
        return self._displacement

    @displacement.setter
    def displacement(self, value):
        self._displacement = np.array(value)

    def inverse(self):
        return EuclideanTransformation(-self._angle,
                                       -np.dot(self._R.T, self._displacement))

    def compose(self, other):
        """Return the composition of self (left) with other (right)

        If g1 = (R1, v1)
           g2 = (R2, v2)
        where R1, R2 are rotation matrices and v1, v2 are displacement vectors,
        then
            g1 g2 = (R1 R2, R1 v2 + v1)
        """
        if other is None:
            return self
        angle = self.angle + other.angle
        displacement = np.dot(self._R, other.displacement) + self._displacement
        return EuclideanTransformation(angle, displacement)

    def xform_position(self, vector):
        """Return the action of the transformation on the given vectors

        `vector` can be an array of length 2 or a 2d-array with 2 rows
        """
        newvector = np.array(vector, copy=True)
        if self._angle:
            newvector = np.dot(self._R, newvector)
        if self._displacement.any():
            if vector.ndim == 1:
                newvector += self._displacement
            else:
                newvector += self._displacement[:, np.newaxis]
        return newvector


class Body(object):
    """Base class for representing bodies
    """
    def __init__(self):
        self._time = 0

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, value):
        self._time = value

    def get_body(self):
        """Return the Body object in the body-fixed frame
        """
        return self

    def get_transformation(self):
        """Return the transformation from the body-fixed to inertial frame
        """
        return None

class Circle(Body):
    """Circle
    """
    def __init__(self, radius, num_points):
        """Return a circle with specified radius and number of points
        """
        super(Circle, self).__init__()
        self._radius = radius
        th = np.linspace(0, 2 * np.pi, num_points)
        self._x = radius * np.cos(th)
        self._y = radius * np.sin(th)

    def get_points(self, **kwargs):
        return self._x, self._y


class Airfoil(Body):
    """NACA 4-digit series airfoil
    """
    def __init__(self, code, num_points, zero_thick_te=False, uniform=False):
        """Return a NACA 4-digit series airfoil
        """
        super(Airfoil, self).__init__()
        # extract parameters from 4-digit code
        code_str = "%04d" % int(code)
        if len(code_str) != 4:
            raise ValueError("NACA designation is more than 4 digits")
        max_camber = 0.01 * int(code_str[0])
        p = 0.1 * int(code_str[1])  # location of max camber
        thickness = 0.01 * int(code_str[2:])
        if uniform:
            x = np.linspace(0, 1, num_points)
        else:
            # closer spacing near leading edge
            theta = np.linspace(0, 0.5 * np.pi, num_points)
            x = 1 - np.cos(theta)

        # thickness
        coefs = [-0.1015, 0.2843, -0.3516, -0.1260, 0, 0.2969]
        if zero_thick_te:
            coefs[0] = -0.1036
        y_thick = 5 * thickness * (np.polyval(coefs[:5], x) +
                                   coefs[5] * np.sqrt(x))

        # camber
        front = np.where(x <= p)
        back = np.where(x > p)
        y_camber = np.zeros_like(x)
        if p:
            y_camber[front] = max_camber * x[front] / p**2 * (2 * p - x[front])
            y_camber[back] = max_camber * ((1. - x[back])/(1. - p)**2 *
                                           (1 + x[back] - 2 * p))
        self._x = np.hstack([x[-1:0:-1], x])
        self._y = np.hstack([y_camber[-1:0:-1] + y_thick[-1:0:-1],
                             y_camber - y_thick])

    def get_points(self, **kwargs):
        return self._x, self._y


class TransformedBody(object):
    """Base class for Euclidean transformations of existing bodies
    """
    def __init__(self, body, angle=0, displacement=(0,0)):
        self._parent = body
        self._body = body.get_body()
        self._transformation = EuclideanTransformation(angle, displacement)

    def get_body(self):
        return self._body

    def get_transformation(self):
        return self._transformation.compose(self._parent.get_transformation())

    @property
    def displacement(self):
        return self._transformation.displacement

    @displacement.setter
    def displacement(self, value):
        self._transformation.displacement = value

    @property
    def angle(self):
        return self._transformation.angle

    @angle.setter
    def angle(self, value):
        self._transformation.angle = value

    @property
    def time(self):
        return self._body.time

    @time.setter
    def time(self, value):
        self._body.time = value

    def get_points(self, body_frame=False):
        x, y = self._body.get_points()
        if body_frame:
            return x, y
        q = self.get_transformation().xform_position(np.vstack([x, y]))
        return q[0,:], q[1,:]


class Pitching(TransformedBody):
    """Sinusoidal pitching for an existing body
    """
    def __init__(self, body, amplitude, frequency, phase=0.):
        super(Pitching, self).__init__(body)
        self._amplitude = amplitude
        self._frequency = frequency
        self._phase = phase * np.pi / 180

    def get_transformation(self):
        self.angle = self._amplitude * np.sin(self._frequency * self.time
                                              + self._phase)
        return super(Pitching, self).get_transformation()


class Heaving(TransformedBody):
    """Sinusoidal heaving for an existing body
    """
    def __init__(self, body, displacement, frequency, phase=0.):
        super(Heaving, self).__init__(body)
        self._displacement = np.array(displacement)
        self._frequency = frequency
        self._phase = phase * np.pi / 180

    def get_transformation(self):
        displacement = self._displacement * np.sin(self._frequency * self.time
                                                   + self._phase)
        self.displacement = displacement
        return super(Heaving, self).get_transformation()


class VortexPanels(object):
    pass

class BoundVortexPanels(object):
    def __init__(self, body):
        self._body = body
        x, y = body.get_points(body_frame=True)
        q = np.vstack([x,y])
        dq = np.diff(q)
        self._numpanels = dq.shape[1]
        self._normals = (np.vstack([dq[1,:], -dq[0,:]]) /
                         np.linalg.norm(dq, axis=0))
        q25 = q[:,:-1] + 0.25 * dq
        q75 = q[:,:-1] + 0.75 * dq
        # vortex positions at 1/4 chord of panel
        # collocation points at 3/4 chord of panel
        # assume first half goes from trailing edge to leading edge,
        #        second half from leading edge back to trailing edge
        half = self._numpanels / 2
        self._xvort = np.hstack([q75[:,:half], q25[:,half:]])
        self._xcoll = np.hstack([q25[:,:half], q75[:,half:]])
        self._gam = np.zeros(self._numpanels)

    def update_positions(self):
        self.panels = self._body.get_points()

    def update_strengths(self, wake, Uinfty, dt):
        # compute influence coefficients and RHS and solve for strengths
        pass

    def get_wake_panels(self):
        return None

    @property
    def vortices(self):
        return self._xvort[0,:], self._xvort[1,:], self._gam

    @property
    def collocation_pts(self):
        return self._xcoll[0,:], self._xcoll[1,:]

    @property
    def normals(self):
        return self._normals[0,:], self._normals[1,:]

class FreeVortexParticles(object):
    def __init__(self):
        pass

    def update(self, body, Uinfty, dt):
        pass

    def add_panels(self, panels):
        pass

    @property
    def vortices(self):
        return 0, 0, 0


class SourceDoubletPanels(object):
    def __init__(self, body):
        self._body = body
        self.panels = body.get_points()

    def update_positions(self):
        self.panels = self._body.get_points()

    def update_strengths(self, wake, Uinfty, dt):
        # compute influence coefficients and RHS and solve for strengths
        pass

    def get_wake_panels(self):
        return None


def time_advance(body, wake, Uinfty, dt):
    # todo: how does dt come in to updating strengths of body panels, and in
    # particular wake panel to be shed?

    # 1) define the wake panel: need Uinf and dt to determine length
    # 2) to determine rhs for update_strengths, need Uinf for relative vel
    # 3) wake update needs Uinf and dt (relative vel)
    body.update_strengths(wake, Uinfty, dt) # might need dt to determine length of TE panel
    wake.update(body, Uinfty, dt)
    shed_panels = body.get_wake_panels()
    wake.add_panels(shed_panels)

def compute_forces(body, wake):
    return 0, 0
