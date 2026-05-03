import cv2
import mediapipe as mp
import time

def load_mediapipe_hands():
    try:
        return mp.solutions.hands, mp.solutions.drawing_utils
    except AttributeError:
        from mediapipe.python.solutions import drawing_utils, hands
        return hands, drawing_utils

class TwoHandGestureTest:
    """Test two-handed gesture classification with laptop webcam"""
    
    def __init__(self):
        # Initialize MediaPipe Hands
        self.mp_hands, self.mp_draw = load_mediapipe_hands()
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        )
        
        # FPS tracking
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0
        
    def is_hand_open(self, hand_landmarks):
        """
        Determine if hand is open or closed based on finger positions
        Returns: True if open, False if closed
        """
        landmarks = hand_landmarks.landmark
        fingers_extended = 0
        
        # Thumb: compare tip (4) with MCP (2)
        # For right hand, thumb extends to the right; for left hand, to the left
        thumb_tip = landmarks[4]
        thumb_mcp = landmarks[2]
        thumb_ip = landmarks[3]
        
        # Check if thumb is extended (tip is farther from palm than IP joint)
        thumb_dist_tip = abs(thumb_tip.x - landmarks[0].x)
        thumb_dist_ip = abs(thumb_ip.x - landmarks[0].x)
        if thumb_dist_tip > thumb_dist_ip:
            fingers_extended += 1
            
        # Other fingers: compare tip Y-coordinate with PIP joint
        # If tip is above (lower Y value) than PIP, finger is extended
        finger_tips = [8, 12, 16, 20]  # Index, Middle, Ring, Pinky tips
        finger_pips = [6, 10, 14, 18]  # Corresponding PIP joints
        
        for tip, pip in zip(finger_tips, finger_pips):
            if landmarks[tip].y < landmarks[pip].y:  # Tip is above PIP (extended)
                fingers_extended += 1
        
        # Hand is "open" if 3 or more fingers extended (including thumb)
        return fingers_extended >= 3, fingers_extended
    
    def get_hand_label(self, handedness):
        """Get left/right hand label"""
        return handedness.classification[0].label
    
    def detect_gesture(self, frame):
        """
        Detect two-handed gesture and return command
        Returns: (command, hand_states, finger_counts)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        command = "STOP"
        hand_states = {}
        finger_counts = {}
        
        if results.multi_hand_landmarks and results.multi_handedness:
            hands_detected = {}
            
            # Process each detected hand
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                hand_label = self.get_hand_label(handedness)
                is_open, finger_count = self.is_hand_open(hand_landmarks)
                
                hands_detected[hand_label] = {
                    'landmarks': hand_landmarks,
                    'open': is_open,
                    'fingers': finger_count
                }
                
                # Draw hand landmarks with connections
                self.mp_draw.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
                
                # Store hand state
                hand_states[hand_label] = "OPEN" if is_open else "CLOSED"
                finger_counts[hand_label] = finger_count
            
            # Determine command based on two-hand gestures
            if 'Left' in hands_detected and 'Right' in hands_detected:
                left_open = hands_detected['Left']['open']
                right_open = hands_detected['Right']['open']
                
                if left_open and right_open:
                    command = "FORWARD ⬆️"  # Both hands open
                elif not left_open and not right_open:
                    command = "BACK ⬇️"     # Both hands closed
                elif right_open and not left_open:
                    command = "RIGHT ➡️"    # Right open, left closed
                elif left_open and not right_open:
                    command = "LEFT ⬅️"     # Left open, right closed
            elif len(hands_detected) == 1:
                command = "STOP (Need 2 hands)"
        
        return command, hand_states, finger_counts
    
    def draw_ui(self, frame, command, hand_states, finger_counts):
        """Draw UI overlay on frame"""
        h, w = frame.shape[:2]
        
        # Create semi-transparent overlay for better text visibility
        overlay = frame.copy()
        
        # Top banner - Command display
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # Command color coding
        cmd_colors = {
            "FORWARD ⬆️": (0, 255, 0),
            "BACK ⬇️": (0, 0, 255),
            "LEFT ⬅️": (255, 255, 0),
            "RIGHT ➡️": (255, 0, 255),
            "STOP": (100, 100, 100)
        }
        
        cmd_color = cmd_colors.get(command, (100, 100, 100))
        
        # Display command (large, centered)
        cmd_text = command if command in cmd_colors else "STOP"
        cv2.putText(frame, cmd_text, (w//2 - 150, 60), 
                    cv2.FONT_HERSHEY_DUPLEX, 1.5, cmd_color, 3)
        
        # Bottom panel - Hand status
        panel_height = 150
        cv2.rectangle(overlay, (0, h - panel_height), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # Left hand status
        left_y = h - 110
        if 'Left' in hand_states:
            left_color = (0, 255, 0) if hand_states['Left'] == "OPEN" else (0, 0, 255)
            left_text = f"LEFT: {hand_states['Left']}"
            finger_text = f"({finger_counts['Left']} fingers)"
        else:
            left_color = (100, 100, 100)
            left_text = "LEFT: NOT DETECTED"
            finger_text = ""
        
        cv2.putText(frame, left_text, (20, left_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, left_color, 2)
        cv2.putText(frame, finger_text, (20, left_y + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, left_color, 2)
        
        # Right hand status
        right_y = h - 110
        if 'Right' in hand_states:
            right_color = (0, 255, 0) if hand_states['Right'] == "OPEN" else (0, 0, 255)
            right_text = f"RIGHT: {hand_states['Right']}"
            finger_text = f"({finger_counts['Right']} fingers)"
        else:
            right_color = (100, 100, 100)
            right_text = "RIGHT: NOT DETECTED"
            finger_text = ""
        
        cv2.putText(frame, right_text, (w//2 + 20, right_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, right_color, 2)
        cv2.putText(frame, finger_text, (w//2 + 20, right_y + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, right_color, 2)
        
        # FPS counter
        cv2.putText(frame, f"FPS: {self.current_fps:.1f}", (w - 120, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Instructions
        instructions = [
            "GESTURE CONTROLS:",
            "Both OPEN = Forward",
            "Both CLOSED = Back",
            "R-Open + L-Closed = Right",
            "L-Open + R-Closed = Left"
        ]
        
        for i, text in enumerate(instructions):
            cv2.putText(frame, text, (20, 120 + i*25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def update_fps(self):
        """Update FPS calculation"""
        self.fps_frame_count += 1
        if self.fps_frame_count >= 30:
            elapsed = time.time() - self.fps_start_time
            self.current_fps = self.fps_frame_count / elapsed
            self.fps_start_time = time.time()
            self.fps_frame_count = 0
    
    def run(self):
        """Run the test application"""
        # Open webcam
        cap = cv2.VideoCapture(0)
        
        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not cap.isOpened():
            print("❌ Error: Could not open webcam")
            return
        
        print("\n" + "="*60)
        print("🤚 Two-Hand Gesture Classification Test")
        print("="*60)
        print("\nGesture Commands:")
        print("  🖐️🖐️  Both Open          → FORWARD")
        print("  ✊✊   Both Closed        → BACK")
        print("  🖐️✊  Right Open + Left Closed  → TURN RIGHT")
        print("  ✊🖐️  Left Open + Right Closed  → TURN LEFT")
        print("\nPress 'q' to quit")
        print("="*60 + "\n")
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("❌ Error: Failed to read frame")
                break
            
            # Flip frame horizontally for mirror effect (more intuitive)
            frame = cv2.flip(frame, 1)
            
            # Detect gestures
            command, hand_states, finger_counts = self.detect_gesture(frame)
            
            # Draw UI
            self.draw_ui(frame, command, hand_states, finger_counts)
            
            # Update FPS
            self.update_fps()
            
            # Display frame
            cv2.imshow("Hand Gesture Test - Press 'q' to quit", frame)
            
            # Check for quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("🔄 Resetting...")
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        self.hands.close()
        print("\n✅ Test completed successfully!")

# Run the test
if __name__ == "__main__":
    test = TwoHandGestureTest()
    test.run()
