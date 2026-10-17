"""MP4 output and animation checks for production motion renderer."""
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import motion_reels as motion
import production_media as media

class ReelTests(unittest.TestCase):
    def test_distinct_photo_categories(self):
        human=media.visual_prompt({'headline':'People','creative_guidance':'Warehouse staff at work'},2)
        utility=media.visual_prompt({'headline':'Utilities','creative_guidance':'Industrial sensors'},3)
        self.assertNotEqual(human,utility)
        self.assertIn('PERSON-FREE',utility)

    def test_resource_limits(self):
        import inspect
        limits=inspect.signature(motion.render_reel).parameters
        self.assertLessEqual(limits['width'].default,540)
        self.assertLessEqual(limits['height'].default,960)
        self.assertLessEqual(limits['fps'].default,18)

    def test_frame_animation(self):
        a=motion.overlay_frame(1,.1,15,2,{'headline':'Industrial planning'},240,426)
        b=motion.overlay_frame(40,2,15,2,{'headline':'Industrial planning'},240,426)
        self.assertNotEqual(a.tobytes(),b.tobytes())

    def test_provider_mp3_frame_variants_are_decoded_not_byte_guessed(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('FFmpeg missing')
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            mp3=Path(folder)/'speech.mp3'
            result=subprocess.run(['ffmpeg','-loglevel','error','-y','-f','lavfi',
                 '-i','sine=frequency=440:duration=2.0','-q:a','8',str(mp3)],
                 capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0)
            client=Mock()
            client.audio.speech.create.return_value.read.return_value=mp3.read_bytes()
            generated=motion.synth_voice(client,{'headline':'Industrial planning'})
            self.assertEqual(generated,mp3.read_bytes())

    def test_real_audio_video_mp4(self):
        if not shutil.which('ffmpeg'):self.skipTest('FFmpeg missing')
        with tempfile.TemporaryDirectory() as folder:
            source=Image.new('RGB',(400,300),(114,145,164))
            original=io.BytesIO();source.save(original,format='PNG')
            voice=Path(folder)/'voice.mp3'
            proc=subprocess.run(['ffmpeg','-loglevel','error','-y','-f','lavfi',
                '-i','sine=frequency=500:duration=2.5','-q:a','8',str(voice)],
                capture_output=True,timeout=35)
            self.assertEqual(proc.returncode,0)
            result=motion.render_reel(original.getvalue(),2,
                {'headline':'Industrial expansion planning'},voice.read_bytes(),
                duration=2.5,width=240,height=426,fps=8)
            saved=Path(folder)/'clip.mp4';saved.write_bytes(result)
            info=motion.probe_video(saved,min_duration=2)
            self.assertIn('video',info['streams'])
            self.assertIn('audio',info['streams'])
