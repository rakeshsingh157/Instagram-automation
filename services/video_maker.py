import os
from moviepy.editor import ImageClip

def create_video_from_image(image_path: str, duration: int = 5) -> str:
    """
    Takes a generated image and converts it into a short mp4 video reel.
    Currently creates a static video spanning `duration` seconds.
    """
    base, _ = os.path.splitext(image_path)
    output_path = f"{base}_video.mp4"
    
    clip = ImageClip(image_path).set_duration(duration)
    
    # Write the video file using a fast preset
    clip.write_videofile(
        output_path, 
        fps=24, 
        codec="libx264", 
        audio=False, 
        preset="ultrafast",
        logger=None # Suppress verbose output
    )
    
    return output_path
