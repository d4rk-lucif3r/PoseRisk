import numpy as np
import torch
import os.path as osp
import json

class REBA:
    def __init__(self):
        self.smpl_joint_names = ('L_Hip', 'R_Hip', 'Torso', 'L_Knee', 'R_Knee', 'Spine', 'L_Ankle', 'R_Ankle', 'Chest', 'L_Toe',
                                'R_Toe', 'Neck', 'L_Thorax', 'R_Thorax', 'Head', 'L_Shoulder', 'R_Shoulder', 'L_Elbow', 'R_Elbow', 'L_Wrist',
                                'R_Wrist', 'L_Hand', 'R_Hand')

        self.table_a = np.array(
            [[[1,2,3,4],[1,2,3,4],[3,3,5,6]],
             [[2,3,4,5],[3,4,5,6],[4,5,6,7]],
             [[2,4,5,6],[4,5,6,7],[5,6,7,8]],
             [[3,5,6,7],[5,6,7,8],[6,7,8,9]],
             [[4,6,7,8],[6,7,8,9],[7,8,9,9]]
            ])

        self.table_b = np.array(
            [[[1,2,2],[1,2,3]],
             [[1,2,3],[2,3,4]],
             [[3,4,5],[4,5,5]],
             [[4,5,5],[5,6,7]],
             [[6,7,8],[7,8,8]],
             [[7,8,8],[8,9,9]]
            ])

        self.table_c = np.array([
            [1,1,1,2,3,3,4,5,6,7,7,7],
            [1,2,2,3,4,4,5,6,6,7,7,8],
            [2,3,3,3,4,5,6,7,7,8,8,8],
            [3,4,4,4,5,6,7,8,8,9,9,9],
            [4,4,4,5,6,7,8,8,9,9,9,9],
            [6,6,6,7,8,8,9,9,10,10,10,10],
            [7,7,7,8,9,9,9,10,10,11,11,11],
            [8,8,8,9,10,10,10,10,10,11,11,11],
            [9,9,9,10,10,10,11,11,11,12,12,12],
            [10,10,10,11,11,11,11,12,12,12,12,12],
            [11,11,11,11,12,12,12,12,12,12,12,12],
            [12,12,12,12,12,12,12,12,12,12,12,12]
        ])

    def __call__(self, poses, add_info):
        results = []

        add_score_a, add_score_b = self.additional_score(add_info)

        for pose in poses:
            # Group A
            group_a_score, group_a_list = self.group_a(pose, add_info)
            group_a_score = group_a_score + add_score_a
            
            # Group B
            group_b_score, group_b_list = self.group_b(pose)
            group_b_score = group_b_score + add_score_b

            # Final Score
            group_a_score = int(np.clip(group_a_score, 1, 12))
            group_b_score = int(np.clip(group_b_score, 1, 12))
            final_score = self.table_c[group_a_score-1][group_b_score-1]
            
            data = {
                'score': final_score,
                'group_a': group_a_score,
                'group_b': group_b_score,
                'log_score': group_a_list+group_b_list
            }
            results.append(data)

        return results, ['trunk', 'neck', 'leg', 'upper_arm', 'lower_arm', 'wrist']
            
            
            
    def group_a(self, pose, add_info):
        trunk, neck, leg = 0,0,0
        trunk += self.trunk_bending(pose)
        trunk += self.trunk_twisted(pose)
        trunk += self.trunk_side_bending(pose)
        neck += self.neck_bending(pose)
        neck += self.neck_side_bending(pose)
        neck += self.neck_twisted(pose)
        leg += self.leg_bending(pose, add_info)

        trunk = int(np.clip(trunk, 1, 5))
        neck = int(np.clip(neck, 1, 3))
        leg = int(np.clip(leg, 1, 4))
        return self.table_a[trunk-1][neck-1][leg-1], [trunk, neck, leg]
      

    def group_b(self, pose):
        upper_arm, lower_arm, wrist = 0,0,0
        upper_arm += self.upper_arm_bending(pose)
        upper_arm += self.shoulder(pose)
        upper_arm += self.upper_arm_aduction(pose)
        lower_arm += self.lower_arm_bending(pose)
        wrist += self.wrist_bending(pose)
        wrist += self.wrist_side_bending(pose)
        wrist += self.wrist_twist(pose)

        upper_arm = int(np.clip(upper_arm, 1, 6))
        lower_arm = int(np.clip(lower_arm, 1, 2))
        wrist = int(np.clip(wrist, 1, 3))
        return self.table_b[upper_arm-1][lower_arm-1][wrist-1], [upper_arm, lower_arm, wrist]
        
    
    def trunk_bending(self, pose):
        idx = self.get_angle_index('Torso', 'BEND1')
        angle = pose[self.smpl_joint_names.index('Torso')][idx]
        
        if angle>= 0 and angle<10: return 1
        elif abs(angle)>=10 and abs(angle)<20: return 2
        elif angle>=20 and angle<60: return 3
        elif angle<=-20: return 3
        elif angle>=60: return 4
        else: return 1

    def trunk_twisted(self, pose):
        idx = self.get_angle_index('Torso', 'TWIST')
        angle = pose[self.smpl_joint_names.index('Torso')][idx]

        if angle>-10 and angle<10: return 0
        elif angle<=-10 or angle>=10: return 1
        else: return 0

    def trunk_side_bending(self, pose):
        idx = self.get_angle_index('Torso', 'BEND2')
        angle = pose[self.smpl_joint_names.index('Torso')][idx]

        if abs(angle)<10: return 0
        elif abs(angle)>=10: return 1
        return 0

    def neck_bending(self, pose):
        idx = self.get_angle_index('Neck', 'BEND1')
        angle = pose[self.smpl_joint_names.index('Neck')][idx]

        if angle>-10 and angle<20: return 1
        elif angle<-10 or angle>=20: return 2
        return 1

    def neck_side_bending(self, pose):
        idx = self.get_angle_index('Neck', 'BEND2')
        angle = pose[self.smpl_joint_names.index('Neck')][idx]

        if angle>-20 and angle<20: return 0
        elif abs(angle)>=20: return 1

    def neck_twisted(self, pose):
        idx = self.get_angle_index('Neck', 'TWIST')
        angle = pose[self.smpl_joint_names.index('Neck')][idx]

        if angle>-20 and angle<20: return 0
        elif abs(angle)>=20: return 1

    def leg_bending(self, pose, add_info):
        score1, score2 = 0, 0
        
        idx = self.get_angle_index('L_Knee', 'BEND1')
        angle = pose[self.smpl_joint_names.index('L_Knee')][idx]

        if angle>=0 and angle<30: score1=0
        elif angle>=30 and angle<=60: score1=1
        elif angle>60 and add_info["sitting"] == 0 : score1=2
        else:
            score1=0

        idx = self.get_angle_index('R_Knee', 'BEND1')
        angle = pose[self.smpl_joint_names.index('R_Knee')][idx]

        if angle>-30 and angle<=0: score2=0
        elif angle>=-60 and angle<=-30: score2=1
        elif angle<-60 and add_info["sitting"] == 0 : score2=2

        return max(score1, score2)

    def upper_arm_bending(self, pose):
        score1, score2 = 0, 0

        idx = self.get_angle_index('L_Shoulder', 'BEND1')
        angle1 = pose[self.smpl_joint_names.index('L_Shoulder')][idx]
        idx = self.get_angle_index('L_Shoulder', 'BEND2')
        angle2 = pose[self.smpl_joint_names.index('L_Shoulder')][idx]
        idx = self.get_angle_index('L_Thorax', 'TWIST')
        angle3 = pose[self.smpl_joint_names.index('L_Thorax')][idx]

        if (angle1>=-90 and angle1<0) and (angle2>=-90 and angle2<0):
            if angle3>=-20 and angle3<=20:
                score1 = 1
            elif (angle3>=-45 and angle3<-20) or (angle3>20):
                score1 = 2
            elif angle3>=-90 and angle3<-45:
                score1 = 3
            elif angle3<-90:
                score1 = 4
            else:
                score1 = 1
        else:
            score1 = 1

        idx = self.get_angle_index('R_Shoulder', 'BEND1')
        angle1 = pose[self.smpl_joint_names.index('R_Shoulder')][idx]
        idx = self.get_angle_index('R_Shoulder', 'BEND2')
        angle2 = pose[self.smpl_joint_names.index('R_Shoulder')][idx]
        idx = self.get_angle_index('R_Thorax', 'TWIST')
        angle3 = pose[self.smpl_joint_names.index('R_Thorax')][idx]

        if (angle1>0 and angle1<=90) and (angle2>0 and angle2<=90):
            if angle3>=-20 and angle3<=20:
                score2 = 1
            elif (angle3>=-45 and angle3<-20) or (angle3>20):
                score2 = 2
            elif angle3>=-90 and angle3<-45:
                score2 = 3
            elif angle3<-90:
                score2 = 4
            else:
                score2 = 1
        else:
            score2 = 1

        return max(score1, score2)

    def shoulder(self, pose):
        score1, score2 = 0, 0

        idx = self.get_angle_index('L_Shoulder', 'BEND1')
        angle1 = pose[self.smpl_joint_names.index('L_Shoulder')][idx]
        idx = self.get_angle_index('L_Shoulder', 'BEND2')
        angle2 = pose[self.smpl_joint_names.index('L_Shoulder')][idx]
        idx = self.get_angle_index('L_Thorax', 'BEND2')
        angle3 = pose[self.smpl_joint_names.index('L_Thorax')][idx]

        if (angle1>=-90 and angle1<0) and (angle2>=-90 and angle2<0):
            if angle3>=0 and angle3<=90:
                score1 = 1
            else:
                score1 = 0
        else:
            score1 = 0

        idx = self.get_angle_index('R_Shoulder', 'BEND1')
        angle1 = pose[self.smpl_joint_names.index('R_Shoulder')][idx]
        idx = self.get_angle_index('R_Shoulder', 'BEND2')
        angle2 = pose[self.smpl_joint_names.index('R_Shoulder')][idx]
        idx = self.get_angle_index('R_Thorax', 'BEND2')
        angle3 = pose[self.smpl_joint_names.index('R_Thorax')][idx]

        if (angle1>0 and angle1<=90) and (angle2>0 and angle2<=90):
            if angle3>=-90 and angle3<=0:
                score2 = 1
            else:
                score2 = 0
        else:
            score2 = 0

        return max(score1, score2)

    def upper_arm_aduction(self, pose):
        score1, score2 = 0, 0

        idx = self.get_angle_index('L_Shoulder', 'BEND2')
        angle = pose[self.smpl_joint_names.index('L_Shoulder')][idx]

        if angle>=-90 and angle<0:
            score1 = 0
        elif angle>=0 and angle<=180:
            score1 = 1
        else:
            score1 = 0
        
        idx = self.get_angle_index('R_Shoulder', 'BEND2')
        angle = pose[self.smpl_joint_names.index('R_Shoulder')][idx]

        if angle>0 and angle<90:
            score2 = 0
        elif angle>=-180 and angle<=180:
            score2 = 1
        else:
            score2 = 0
        
        return max(score1, score2)


    def lower_arm_bending(self, pose):
        score1, score2 = 0, 0
        idx = self.get_angle_index('L_Shoulder', 'BEND1')
        angle1 = pose[self.smpl_joint_names.index('L_Shoulder')][idx]
        idx = self.get_angle_index('L_Shoulder', 'BEND2')
        angle2 = pose[self.smpl_joint_names.index('L_Shoulder')][idx]
        idx = self.get_angle_index('L_Elbow', 'BEND1')
        angle3 = pose[self.smpl_joint_names.index('L_Elbow')][idx]

        if (angle1>=-90 and angle1<0) and (angle2>=-90 and angle2<0):
            if angle3>=-100 and angle3<=-60:
                score1 = 1
            elif (angle3>=-180 and angle3<-100) or (angle3>-60 and angle3<=0):
                score1 = 2
            else:
                score1 = 1
        else:
            score1 = 1

        idx = self.get_angle_index('R_Shoulder', 'BEND1')
        angle1 = pose[self.smpl_joint_names.index('R_Shoulder')][idx]
        idx = self.get_angle_index('R_Shoulder', 'BEND2')
        angle2 = pose[self.smpl_joint_names.index('R_Shoulder')][idx]
        idx = self.get_angle_index('R_Elbow', 'BEND1')
        angle3 = pose[self.smpl_joint_names.index('R_Elbow')][idx]

        if (angle1>0 and angle1<=90) and (angle2>0 and angle2<=90):
            if angle3>=60 and angle3<=100:
                score2 = 1
            elif (angle3>=0 and angle3<60) or (angle3>100 and angle3<=180):
                score2 = 2
            else:
                score2 = 1
        else:
            score2 = 1
        
        return max(score1, score2)

    def wrist_bending(self, pose):
        score1, score2 = 0, 0
        idx = self.get_angle_index('L_Wrist', 'BEND2')
        angle = pose[self.smpl_joint_names.index('L_Wrist')][idx]

        if abs(angle)<15:
            score1 = 1
        elif abs(angle)>=15:
            score1 = 2
        else:
            score1 = 1
        
        idx = self.get_angle_index('R_Wrist', 'BEND2')
        angle = pose[self.smpl_joint_names.index('R_Wrist')][idx]

        if abs(angle)<15:
            score2 = 1
        elif abs(angle)>=15:
            score2 = 2
        else:
            score2 = 1
        
        return max(score1, score2)

    def wrist_side_bending(self, pose):
        score1, score2 = 0, 0
        idx = self.get_angle_index('L_Wrist', 'BEND1')
        angle = pose[self.smpl_joint_names.index('L_Wrist')][idx]

        if abs(angle)<15:
            score1 = 0
        elif abs(angle)>=15:
            score1 = 1
        else:
            score1 = 0
        
        idx = self.get_angle_index('R_Wrist', 'BEND1')
        angle = pose[self.smpl_joint_names.index('R_Wrist')][idx]

        if abs(angle)<15:
            score2 = 0
        elif abs(angle)>=15:
            score2 = 1
        else:
            score2 = 0
        
        return max(score1, score2)
    
    def wrist_twist(self, pose):
        score1, score2 = 0, 0
        idx = self.get_angle_index('L_Wrist', 'TWIST')
        angle = pose[self.smpl_joint_names.index('L_Wrist')][idx]

        if abs(angle)<15:
            score1 = 0
        elif abs(angle)>=15:
            score1 = 1
        else:
            score1 = 0
        
        idx = self.get_angle_index('R_Wrist', 'BEND1')
        angle = pose[self.smpl_joint_names.index('R_Wrist')][idx]

        if abs(angle)<15:
            score2 = 0
        elif abs(angle)>=15:
            score2 = 1
        else:
            score2 = 0
        
        return max(score1, score2)

    def additional_score(self, add_info):
        score_a = add_info["whole_load/force"] + add_info["leg_posture"]
        score_b = add_info["arm_contact"] + add_info["handle_exist"]
        return score_a, score_b

    def get_angle_index(self, joint, direction):
        if joint not in ('L_Thorax', 'R_Thorax', 'L_Shoulder', 'R_Shoulder', 'L_Elbow', 'R_Elbow', 'L_Wrist', 'R_Wrist', 'L_Hand', 'R_Hand'):
            if direction == 'BEND1':
                return 0
            elif direction == 'BEND2':
                return 2
            else:
                return 1
        else:
            if direction == 'BEND1':
                return 1
            elif direction == 'BEND2':
                return 2
            else:
                return 0


class RULA:
    def __init__(self):
        self.smpl_joint_names = ('L_Hip', 'R_Hip', 'Torso', 'L_Knee', 'R_Knee', 'Spine', 'L_Ankle', 'R_Ankle', 'Chest', 'L_Toe',
                                'R_Toe', 'Neck', 'L_Thorax', 'R_Thorax', 'Head', 'L_Shoulder', 'R_Shoulder', 'L_Elbow', 'R_Elbow', 'L_Wrist',
                                'R_Wrist', 'L_Hand', 'R_Hand')

    def __call__(self, input_path, output_path):
        # data processing (tracking)
        image_folder, bboxes, frames = self.data_loader(input_path, output_path)
        
        dataset = CropDataset(
            image_folder=image_folder,
            frames=frames,
            bboxes=bboxes,
            joints2d=None,)