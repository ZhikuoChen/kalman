import matplotlib.pyplot as pl

pl.rcParams['legend.loc'] = 'best'
import numpy as np
from numpy import dot
from scipy.linalg import inv


def build_real_values():
    num_of_time_steps = 702
    dt = 0.2
    t = np.linspace(start=0., stop=num_of_time_steps * dt, num=num_of_time_steps)
    s = np.zeros((num_of_time_steps, 2))
    v = np.zeros((num_of_time_steps, 2))
    a_tan = np.zeros((num_of_time_steps, 2))
    a_r = np.zeros((num_of_time_steps, 2))
    a = np.zeros((num_of_time_steps, 2))
    theta = np.zeros((num_of_time_steps, 1))
    omega = np.zeros((num_of_time_steps, 1))
    alpha = np.zeros((num_of_time_steps, 1))

    # Build accelaration profile
    a_tan[0:10, 0] = np.linspace(0.1, 1.0, num=10)
    a_tan[0:10, 1] = a_tan[0:10, 0] ** 2
    a_tan[100:110, 0] = np.linspace(-0.1, -2., num=10)
    a_tan[100:110, 1] = a_tan[100:110, 0] ** 2
    a_tan[150:200, 0] = (np.linspace(-2., 8., num=50) ** 2) / 500
    a_tan[150:200, 1] = (a_tan[150:200, 0] ** 3) / 10
    a_tan[300:400, 0] = (np.linspace(8., -10., num=100) ** 3) / 1000
    a_tan[300:400, 1] = (np.linspace(8., -10., num=100) ** 3) / 1000
    a_tan[500:520, 0] = np.linspace(a_tan[400, 0], -1., num=20) ** 2
    a_tan[500:600, 1] = np.linspace(a_tan[400, 1], 1., num=100)
    a_tan[650:700, 0] = -np.linspace(a_tan[600, 0], 0., num=50)
    a_tan[650:700, 1] = -np.linspace(a_tan[600, 1], 0., num=50)

    a_tan /= 10

    for i in range(1, num_of_time_steps):
        v[i] = v[i - 1] + a_tan[i] * dt
        s[i] = s[i - 1] + v[i] * dt + 0.5 * a[i] * dt ** 2

    # v = np.cumsum(a_tan, axis=0)  # integrate to gain velocity
    # s = np.cumsum(v, axis=0)  # integrate to gain position
    v[0] = 0.1
    theta = np.tanh(np.divide(v[:, 1], v[:, 0]))  # obtain heading from ds or v
    omega = np.diff(theta, axis=0)  # obtain omega from differentiating theta
    alpha = np.diff(omega, axis=0)  # obtain alpha from differentiating omega

    # All array's to the same length
    t = t[2:num_of_time_steps]
    s = s[2:num_of_time_steps]
    v = v[2:num_of_time_steps]
    a_tan = a_tan[2:num_of_time_steps]
    a_r = a_r[2:num_of_time_steps]
    theta = theta[2:num_of_time_steps]
    omega = omega[1:num_of_time_steps]
    num_of_time_steps -= 2

    a = a_tan + a_r  # ignore acceleration due to rotation for now

    return [t, dt, s, v, a, theta, omega, alpha]


def build_measurement_values(t, real_values):
    # Add disturbance to accelerated forces
    a_m = np.random.normal(0, 0.05, (2, len(real_values[0]))).transpose() + real_values[0]

    # Add disturbance and drift to rotational speed
    omega_m = np.random.normal(0, 0.05, (len(real_values[1]), 1))[:, 0] + real_values[1]
    drift_mu = 5e-2
    drift_sigma = 1e-3
    drift = np.ones((real_values[1].size,)) * np.random.normal(drift_mu, drift_sigma)
    omega_m += drift

    z = np.zeros((t.size, 3, 1))
    z[:, 0] = np.reshape(a_m[:, 0], (t.size, 1))
    z[:, 1] = np.reshape(a_m[:, 1], (t.size, 1))
    z[:, 2] = np.reshape(omega_m, (t.size, 1))
    return z


def build_control_values(t, real_values):
    u = np.zeros((t.size, 2, 1))
    u[:, 0] = np.reshape(real_values[:, 0], (t.size, 1))
    u[:, 1] = np.reshape(real_values[:, 1], (t.size, 1))
    return u


def init_kalman(t, dt):
    phi_s = 2

    F = np.array([
        [1., 0., 0.5 * dt ** 2, 0., 0., 0., 0., 0., 0.],
        [0., 0., dt, 0., 0., 0., 0., 0., 0.],
        [0., 0., 1., 0., 0., 0., 0., 0., 0.],
        [0., 0., 0., 1., 0., 0.5 * dt ** 2, 0., 0., 0.],
        [0., 0., 0., 0., 0., dt, 0., 0., 0.],
        [0., 0., 0., 0., 0., 1., 0., 0., 0., ],
        [0., 0., 0., 0., 0., 0., 1., dt, 0.5 * dt ** 2],
        [0., 0., 0., 0., 0., 0., 0., 1., dt],
        [0., 0., 0., 0., 0., 0., 0., 0., 1.]
    ])

    B = np.array([
        [dt, 0.],
        [1., 0.],
        [0., 0.],
        [0., dt],
        [0., 1.],
        [0., 0.],
        [0., 0.],
        [0., 0.],
        [0., 0.]
    ])

    H = np.array([
        [0., 0., 0.],
        [0., 0., 0.],
        [1., 0., 0.],
        [0., 0., 0.],
        [0., 0., 0.],
        [0., 1., 0.],
        [0., 0., 0.],
        [0., 0., 1.],
        [0., 0., 0]
    ])

    Q = np.array([
        [0.05 * dt ** 5, 0., 0.1666 * dt ** 3, 0., 0., 0., 0., 0., 0.],
        [0., 0., 0., 0., 0., 0., 0., 0., 0.],
        [0.1666 * dt ** 3, 0., dt, 0., 0., 0., 0., 0., 0.],
        [0., 0., 0., 0.05 * dt ** 5, 0., 0.1666 * dt ** 3, 0., 0., 0.],
        [0., 0., 0., 0., 0., 0., 0., 0., 0.],
        [0., 0., 0., 0.1666 * dt ** 3, 0., dt, 0., 0., 0.],
        [0., 0., 0., 0., 0., 0., 0.05 * dt ** 5, 0.125 * dt ** 4, 0.1666 * dt ** 3],
        [0., 0., 0., 0., 0., 0., 0.125 * dt ** 4, 0.333 * dt ** 3, 0.5 * dt ** 2],
        [0., 0., 0., 0., 0., 0., 0.1666 * dt ** 3, 0.5 * dt ** 2, dt]
    ]) * phi_s

    R = np.array([
        [9e-1, 0., 0.],
        [0., 9e-1, 0.],
        [0., 0., 2.e-3],
    ]) * 100
    v = np.random.normal(0, 25e-1, (t.size, 3, 1)) * 0
    w = np.random.normal(0, 25e-1, (t.size, 9, 1)) * 0
    return [F, B, H, Q, R, v, w]


def kalman(t, kalman_values, u, z, error):
    x = np.zeros((t.size, 9, 1))
    P = np.zeros((t.size, 9, 9))
    P[0, :, :] = np.array([
        [error[0] ** 2, 0., 0., 0., 0., 0., 0., 0., 0.],
        [0., error[0] ** 2, 0., 0., 0., 0., 0., 0., 0.],
        [0., 0., error[1] ** 2, 0., 0., 0., 0., 0., 0.],
        [0., 0., 0., error[1] ** 2, 0., 0., 0., 0., 0.],
        [0., 0., 0., 0., error[2] ** 2, 0., 0., 0., 0.],
        [0., 0., 0., 0., 0., error[2] ** 2, 0., 0., 0.],
        [0., 0., 0., 0., 0., 0., error[3] ** 2, 0., 0.],
        [0., 0., 0., 0., 0., 0., 0., error[4] ** 2, 0.],
        [0., 0., 0., 0., 0., 0., 0., 0., error[5] ** 2]
    ])

    xhat = np.zeros((t.size, 9, 1))
    y = np.zeros((t.size, 3, 1))

    F = kalman_values[0]
    B = kalman_values[1]
    H = kalman_values[2]
    Q = kalman_values[3]
    R = kalman_values[4]
    v = kalman_values[5]
    w = kalman_values[6]

    K = np.zeros((t.size, 9, 3))

    for k in range(1, t.size):
        xhat[k] = dot(F, x[k - 1]) + dot(B, u[k]) + w[k]
        Phat = dot(F, dot(P[k - 1], F.T)) + Q

        y[k] = z[k] - dot(H.T, xhat[k]) + v[k]

        S = dot(H.T, dot(Phat, H)) + R
        S = np.linalg.inv(S)
        K[k] = dot(Phat, dot(H, S))
        x[k] = xhat[k] + dot(K[k], y[k])

        P[k] = dot(np.eye(9) - dot(K[k], H.T), Phat)
    return [x, K, P, xhat, y]


def NEES(xs, est_xs, ps):
    est_err = xs - est_xs
    err = np.zeros(xs[:, 0].size)
    i = 0
    for x, p in zip(est_err, ps):
        err[i] = (np.dot(x.T, inv(p)).dot(x))
        i += 1
    return err


def plot_results(t, x, xground, y, K, P, xhat, z, nees):
    pl.figure(0)
    pl.grid(True)
    pl.plot(xground[:, 0], xground[:, 3], '.', label='s')
    pl.plot(x[:, 0], x[:, 3], 'x', label='x')
    pl.ylabel('y [m]')
    pl.xlabel('x [m]')
    pl.legend()
    pl.show()

    pl.figure(1)
    pl.subplot(311)
    pl.plot(t, xground[:, 2], label='a')
    pl.plot(t, x[:, 2], 'x', label='x')
    pl.plot(t, z[:, 0], '.', label='y')
    pl.xlabel('Time [s]')
    pl.ylabel('A_x [m/s^2]')
    pl.legend()
    pl.subplot(312)
    pl.plot(t, xground[:, 1], label='v')
    pl.plot(t, x[:, 1], 'x', label='x')
    pl.xlabel('Time [s]')
    pl.ylabel('v_x [m/s]')
    pl.legend()
    pl.subplot(313)
    pl.plot(t, nees, label='NEES')
    pl.legend()
    pl.tight_layout()
    pl.show()

def save_results(t, xground, x, nees):
    # save csv
    datPos = np.zeros((t.size, 4, 1))
    datPos[:, 1] = xground[:, 0]
    datPos[:, 2] = xground[:, 3]
    datPos[:, 2] = x[:, 0]
    datPos[:, 3] = x[:, 3]
    np.savetxt('2DBotPos.dat', datPos, delimiter=',')

    datNEES = np.zeros((t.size, 2, 1))
    datNEES[:, 0] = t.reshape((t.size, 1))
    datNEES[:, 1] = nees.reshape(t.size, 1)
    np.savetxt('2DBot_NEES.dat', datNEES)

def construct_xground(s, v, a, theta, omega, alpha, shape):
    xground = np.zeros(shape)
    xground[:, 0] = s[:, 0].reshape(s[:, 0].size, 1)
    xground[:, 3] = s[:, 1].reshape(s[:, 1].size, 1)
    xground[:, 1] = v[:, 0].reshape(v[:, 0].size, 1)
    xground[:, 4] = v[:, 1].reshape(v[:, 1].size, 1)
    xground[:, 2] = a[:, 0].reshape(a[:, 0].size, 1)
    xground[:, 5] = a[:, 1].reshape(a[:, 1].size, 1)
    xground[:, 6] = theta.reshape(theta.size, 1)
    xground[:, 7] = omega.reshape(omega.size, 1)
    xground[:, 8] = alpha.reshape(alpha.size, 1)
    return xground


def main():
    [t, dt, s, v, a, theta, omega, alpha] = build_real_values()
    z = build_measurement_values(t, [a, omega])
    u = build_control_values(t, v)
    [F, B, H, Q, R, vv, w] = init_kalman(t, dt)
    error = [5, 0.05, 0.5, 0.5, 0.2, 0.4]
    kalman_values = [F, B, H, Q, R, vv, w]
    x, K, P, xhat, y = kalman(t, kalman_values, u, z, error)
    xground = construct_xground(s, v, a, theta, omega, alpha, x.shape)
    nees = NEES(xground, x, P)
    print(np.mean(nees))
    save_results(t, xground, x, nees)
    plot_results(t, x, xground, y, K, P, xhat, z, nees)


if __name__ == '__main__':
    main()
