### Setup detectron2 logger
import detectron2
from detectron2.utils.logger import setup_logger
setup_logger()

### import some common libraries
import numpy as np
import torch
import json,os,cv2,random
import copy

### import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data import detection_utils as utils
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
import detectron2.data.transforms as T
from detectron2.data import build_detection_test_loader
import sys
sys.path.append('/SSD4/kyeongsoo/implant_code/')
from vis_utils import *

# 추가 1
def custom_mapper(dataset_dict):
    dataset_dict = copy.deepcopy(dataset_dict)  # it will be modified by code below
    image = utils.read_image(dataset_dict["file_name"], format='BGR')
    transform_list = [
        T.Resize((300,600))
    ]
    image, transforms = T.apply_transform_gens(transform_list, image)
    dataset_dict["image"] = torch.as_tensor(image.transpose(2, 0, 1).astype("float32"))
    annos = [
        utils.transform_instance_annotations(obj, transforms, image.shape[:2])
        for obj in dataset_dict.pop("annotations")
        if obj.get("iscrowd", 0) == 0
    ]
    instances = utils.annotations_to_instances(annos, image.shape[:2])
    dataset_dict["instances"] = utils.filter_empty_instances(instances)
    return dataset_dict

class CustomPredictor(DefaultPredictor):
    @classmethod
    def build_eval_loader(cls, cfg):
        return build_detection_test_loader(cfg, 'test' , custom_mapper)

def main():

    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml"))
    cfg.DATASETS.TRAIN = ("train_dataset",)
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 4

    # valid set 등록하기
    register_coco_instances("train", {}, "/SSD4/kyeongsoo/implant/Empty_Detection/train/json/missing_teeth_inst.json", "/SSD4/kyeongsoo/implant/Empty_Detection/train/img")

    ### PREDICTION
    # 여기 모델 가중치 불러옴. 원래 주석
    cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "/SSD4/kyeongsoo/implant_code/output/det_50000.pth") ## 이거 이름 바꿔가면서 하기!
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.01   # set the testing threshold for this model
    cfg.DATASETS.TEST = ("train", )
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 512
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 28
    predictor = CustomPredictor(cfg)

    my_dataset_val_metadata = MetadataCatalog.get("train")
    dataset_dicts = DatasetCatalog.get("train")

    ### 파일 한개로 예측해보기 ###
    from detectron2.utils.visualizer import ColorMode


    path = dataset_dicts[0] # 예측할 이미지를 변경
    im = custom_mapper(path) # valid에서 한장 꺼내와서 예측하기
    
    
    # im = dataset_dicts[0]

    im = cv2.imread(im["file_name"])
    outputs = predictor(im)

    print(path['file_name'].split('/')[-1])

    # outputs = predictor(im)
    # 예측 결과를 이미지 위에 나타내준다.

    #####
    ori_img_path = '/SSD4/kyeongsoo/implant/Instance_Segmentation/train/'
    ori_img_path = os.path.join(ori_img_path, path['file_name'].split('/')[-1][:-8].split('.')[0]+'.jpg') ## 파노라마 이미지 위에 나타내기 위해서
    ori_img = detectron2.data.detection_utils.read_image(ori_img_path, format='BGR')
    ori_img = cv2.resize(ori_img, (600, 300))

    #####
    v = Visualizer2(im[:, :, ::-1], MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), scale=1.2)
    #v = Visualizer2(ori_img, MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), scale=1.2)
    v = v.draw_instance_predictions(outputs["instances"].to("cpu"))

    print(cfg.DATASETS.TRAIN[0])

    print(MetadataCatalog.get(cfg.DATASETS.TRAIN[0]))

    # cv2.imshow('', v.get_image()[:, :, ::-1])
    cv2.imwrite('/SSD4/kyeongsoo/implant_code/trainpred.jpg', v.get_image()[:, :, ::-1]) # 이미지 저장
    print("done")

main()