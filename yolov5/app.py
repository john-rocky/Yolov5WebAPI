import cv2
import torch, time, base64
import numpy as np
from pathlib import Path

from models.experimental import attempt_load
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadStreams
from utils.general import (LOGGER, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_coords, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, time_sync
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device

CONF_THRESH = 0.25
IOU_THRESH = 0.45
WORK_JPG = '/tmp/in.png'
SAVE_PATH = '/tmp/out.png'

def handler(event, context):
    device = select_device('cpu')
    
    # load_model
    model =attempt_load('yolov5s.pt')
    stride = int(model.stride.max())
    imgsz = check_img_size(640, s=stride)
    
    img_bin = base64.b64decode(event['img'].encode('utf-8'))
    img_array = np.frombuffer(img_bin,dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    cv2.imwrite(WORK_JPG,img)
    dataset = LoadImages(WORK_JPG, img_size=imgsz, stride=stride)
    names = model.module.names if hasattr(model, 'module') else model.names
    # colors = [[np.random.randint(0, 255) for _ in range(3)] for _ in names]
    save_dir = increment_path(Path("./") / "", exist_ok=False)  #
    t0 = time.time()
    seen, windows, dt = 0, [], [0.0, 0.0, 0.0]
    
    for path, img, im0s, vid_cap, s in dataset:
        img = torch.from_numpy(img).to(device).float()
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        # t1 = time_synchronized()
        pred = model(img, augment=True)[0]

        # Apply NMS
        pred = non_max_suppression(pred, CONF_THRESH, IOU_THRESH, classes=None, agnostic=False)
        # t2 = time_synchronized()
    
        # Process detections
        for i, det in enumerate(pred):  # detections per image
            p, s, im0, frame = path, '', im0s, getattr(dataset, 'frame', 0)
            p = Path(p)
            annotator = Annotator(im0, line_width=3, example=str(names))

            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0
            if len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string
                
                # Write results

                
                for *xyxy, conf, cls in reversed(det):
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                    line = (cls, *xywh)  # label format
                    with open(f'result.txt', 'a') as f:
                        f.write(('%g ' * len(line)).rstrip() % line + '\n')

                    c = int(cls)  # integer class
                    label = (f'{names[c]} {conf:.2f}')
                    annotator.box_label(xyxy, label, color=colors(c, True))
                    save_one_box(xyxy, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)
        cv2.imwrite(SAVE_PATH, im0)
    with open(SAVE_PATH,'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    print("done")
    response = {'img':img_b64}
    return response

if __name__ == '__main__':
    input_file = './data/images/bus.jpg'
    data = {}
    with open(input_file,'rb') as f:
        data['img']= base64.b64encode(f.read()).decode('utf-8')
    output_b64 = handler(data,'context')
    img_bin = base64.b64decode(output_b64['img'].encode('utf-8'))
    img_array = np.frombuffer(img_bin,dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    cv2.imwrite('./out.png',img)
    exit()
