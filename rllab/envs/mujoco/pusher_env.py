import numpy as np

from rllab.core.serializable import Serializable
from rllab.envs.base import Step
from rllab.envs.mujoco.mujoco_env import MujocoEnv
from rllab.misc import logger
from rllab.misc.overrides import overrides


def smooth_abs(x, param):
    return np.sqrt(np.square(x) + np.square(param)) - param


class PusherEnv(MujocoEnv, Serializable):

    FILE = None #'pusher.xml'

    def __init__(self, *args, **kwargs):
        self.__class__.FILE = kwargs['xml_file']
        #kwargs.pop('xml_file')
        super(PusherEnv, self).__init__(*args, **kwargs)
        Serializable.__init__(self, *args, **kwargs)

    def get_current_obs(self):
        return np.concatenate([
            self.model.data.qpos.flat[:7],
            self.model.data.qvel.flat[:7],
            self.get_body_com("tips_arm"),
            self.get_body_com("object"),
            self.get_body_com("goal"),
        ])

    #def get_body_xmat(self, body_name):
    #    idx = self.model.body_names.index(body_name)
    #    return self.model.data.xmat[idx].reshape((3, 3))

    def get_body_com(self, body_name):
        idx = self.model.body_names.index(body_name)
        return self.model.data.com_subtree[idx]

    def step(self, action):
        self.forward_dynamics(action)
        next_obs = self.get_current_obs()

        vec_1 = self.get_body_com("object") - self.get_body_com("tips_arm")
        vec_2 = self.get_body_com("object") - self.get_body_com("goal")
        reward_near = - np.linalg.norm(vec_1)
        reward_dist = - np.linalg.norm(vec_2)
        reward_ctrl = - np.square(action).sum()
        reward = reward_dist + 0.1 * reward_ctrl + 0.5 * reward_near

        done = False
        return Step(next_obs, reward, done)

    @overrides
    def reset(self, init_state=None):
        qpos = self.init_qpos.copy()
        self.goal_pos = np.asarray([0, 0])

        while True:
            self.obj_pos = np.concatenate([
                    np.random.uniform(low=-0.3, high=0, size=1),
                    np.random.uniform(low=-0.2, high=0.2, size=1)])
            if np.linalg.norm(self.obj_pos - self.goal_pos) > 0.17:
                break

        qpos[-4:-2,0] = self.obj_pos
        qpos[-2:,0] = self.goal_pos
        qvel = self.init_qvel + np.random.uniform(low=-0.005,
                high=0.005, size=self.model.nv)
        setattr(self.model.data, 'qpos', qpos)
        setattr(self.model.data, 'qvel', qvel)
        self.model.data.qvel = qvel
        self.model._compute_subtree()
        self.model.forward()

        #self.reset_mujoco(init_state)
        #self.model.forward()
        self.current_com = self.model.data.com_subtree[0]
        self.dcom = np.zeros_like(self.current_com)
        return self.get_current_obs()

    @overrides
    def log_diagnostics(self, paths):
        pass
