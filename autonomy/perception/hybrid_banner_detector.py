import cv2
import numpy as np

class HybridBannerDetector:
    def __init__(self):
        # Tighter green mask is working perfectly!
        self.lower_green = np.array([45, 100, 80])
        self.upper_green = np.array([75, 255, 255])
        
        # Minimum size requirement
        self.min_area = 1000 

    def detect(self, frame):
        # 0. Get screen dimensions to calculate errors
        height, width = frame.shape[:2]
        screen_center_x = width // 2
        screen_center_y = height // 2

        result = {
            "detected": False,
            "bbox": None,
            "center": None,
            "area": 0,
            "error_x": 0, # Added for velocity control
            "error_y": 0, # Added for velocity control
            "debug_frame": frame.copy()
        }
        
        # 1. COLOR DETECTION
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # 2. MORPHOLOGICAL CLEANUP
        kernel = np.ones((5,5), np.uint8)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        
        # --- PICTURE IN PICTURE DEBUG ---
        mask_small = cv2.resize(green_mask, (160, 120))
        mask_bgr = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
        result["debug_frame"][0:120, 0:160] = mask_bgr
        cv2.rectangle(result["debug_frame"], (0, 0), (160, 120), (255, 255, 255), 1)
        cv2.putText(result["debug_frame"], "MASK", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        # --------------------------------
        
        # Find contours of the green blobs
        contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                
                # 3. ASPECT RATIO CHECK
                aspect_ratio = w / float(h)
                if 0.8 < aspect_ratio < 5.0:
                    
                    # 4. SHAPE DETECTION
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.05 * peri, True)
                    
                    if 4 <= len(approx) <= 16:
                        
                        # 5. EXTENT CHECK
                        rect_area = w * h
                        extent = float(area) / rect_area
                        
                        if extent > 0.15: 
                            valid_contours.append(cnt)
                        else:
                            cv2.putText(result["debug_frame"], f"REJ: Extent {extent:.2f}", (x, y-5), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                    else:
                        cv2.putText(result["debug_frame"], f"REJ: {len(approx)} sides", (x, y-5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                else:
                    cv2.putText(result["debug_frame"], f"REJ: AR {aspect_ratio:.2f}", (x, y-5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        if not valid_contours:
            # Draw camera center crosshairs even when nothing is detected
            cv2.line(result["debug_frame"], (screen_center_x, 0), (screen_center_x, height), (255, 255, 255), 1)
            cv2.line(result["debug_frame"], (0, screen_center_y), (width, screen_center_y), (255, 255, 255), 1)
            return result
            
        best_contour = max(valid_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(best_contour)
        
        center_x = x + (w // 2)
        center_y = y + (h // 2)
        
        result["detected"] = True
        result["bbox"] = (x, y, w, h)
        result["center"] = (center_x, center_y)
        result["area"] = cv2.contourArea(best_contour)
        
        # Calculate the crucial error offset values for the mission runner
        result["error_x"] = center_x - screen_center_x
        result["error_y"] = center_y - screen_center_y
        
        # Draw bounding box and target center
        cv2.rectangle(result["debug_frame"], (x, y), (x+w, y+h), (0, 255, 0), 3)
        cv2.circle(result["debug_frame"], (center_x, center_y), 5, (0, 0, 255), -1)
        cv2.putText(result["debug_frame"], "BANNER LOCKED", (x, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Draw absolute camera crosshairs
        cv2.line(result["debug_frame"], (screen_center_x, 0), (screen_center_x, height), (255, 255, 255), 1)
        cv2.line(result["debug_frame"], (0, screen_center_y), (width, screen_center_y), (255, 255, 255), 1)
        
        return result
