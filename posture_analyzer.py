import cv2
import mediapipe as mp
import requests
import time
import schedule
import math
import ctypes

# 用户配置区
BLYNK_AUTH_TOKEN = "你的Blynk Token"
CAPTURE_INTERVAL_MINUTES = 40
BLYNK_API_URL = "https://blynk.cloud/external/api/update"
# 配置结束 


# 全局变量与初始化 
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(static_image_mode=True, model_complexity=1, min_detection_confidence=0.5)

def get_screen_resolution():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except:
        return 1920, 1080

def show_privacy_popup():
    msg = (
        "Welcome to the Posture Assistant!\n\n"
        "This program will analyze your posture using the camera every {} minutes.\n"
        "Only coordinate data is processed. Raw images are NEVER saved or uploaded.\n\n"
        "You can close this program anytime from the Task Manager."
    ).format(CAPTURE_INTERVAL_MINUTES)
    
    ctypes.windll.user32.MessageBoxW(0, msg, "Privacy Notice", 0x40 | 0x1)

def analyze_and_send_to_blynk():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting posture analysis...")
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("ERROR: Cannot open camera. Please check if it's used by another application.")
        return

    # 读取几帧来确保图像稳定
    for _ in range(5):
        cap.read()
        
    success, image = cap.read()
    cap.release() 

    if not success:
        print("ERROR: Failed to capture image from camera.")
        return

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

        if all(p.visibility > 0.6 for p in [nose, left_shoulder, right_shoulder]):
            # 头部前倾比（量化：0~1，0为正常，越大越前倾，建议阈值0.08~0.15）
            shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2
            head_forward_ratio = abs(nose.x - shoulder_mid_x)
            head_forward_ratio = min(max(head_forward_ratio, 0), 0.2)  # 限制最大值

            # 肩膀倾斜角度（量化：-45~+45度，0为水平，正负表示左右高低肩）
            shoulder_tilt_rad = math.atan2(right_shoulder.y - left_shoulder.y, right_shoulder.x - left_shoulder.x)
            shoulder_tilt_angle = math.degrees(shoulder_tilt_rad)
            shoulder_tilt_angle = max(-45, min(45, shoulder_tilt_angle))

            # 姿态综合评分（100分满分，头前倾>0.12或肩膀倾斜>10度则扣分，最低0分）
            score = 100
            if head_forward_ratio > 0.12:
                score -= int((head_forward_ratio - 0.12) * 1000)  # 每超出0.01扣10分
            if abs(shoulder_tilt_angle) > 10:
                score -= int((abs(shoulder_tilt_angle) - 10) * 2)  # 每超1度扣2分
            score = max(0, min(100, score))

            params = {
                'token': BLYNK_AUTH_TOKEN,
                'v0': f"{head_forward_ratio:.4f}",
                'v1': f"{shoulder_tilt_angle:.2f}",
                'v2': score
            }

            print(f"Analysis result: HeadRatio={params['v0']}, ShoulderAngle={params['v1']}, Score={params['v2']}")

            try:
                response = requests.get(BLYNK_API_URL, params=params, timeout=10)
                if response.status_code == 200:
                    print("Data sent to Blynk successfully.")
                else:
                    print(f"ERROR: Blynk server returned status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"ERROR: Could not connect to Blynk server. Check your internet connection. {e}")
        else:
            print("WARNING: Some key body landmarks are not visible. Skipping this analysis.")
    else:
        print("INFO: No person detected. Make sure you are in front of the camera.")

    # 显示调试窗口
    debug_image = image.copy()
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            debug_image,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )
    cv2.imshow('Debug Window - Press Any Key to Continue', debug_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if BLYNK_AUTH_TOKEN == "你的Blynk Token":
        ctypes.windll.user32.MessageBoxW(0, "Please configure your Blynk token in the Python script!", "Configuration Error", 0x10)
        exit()

    show_privacy_popup()

    print(f"Task scheduler started. Analysis will run every {CAPTURE_INTERVAL_MINUTES} minutes.")
    print("This window can be minimized. The script is running in the background.")
    schedule.every(CAPTURE_INTERVAL_MINUTES).minutes.do(analyze_and_send_to_blynk)
    
    analyze_and_send_to_blynk() 

    while True:
        schedule.run_pending()
        time.sleep(1)