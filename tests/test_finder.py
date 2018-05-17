#!/usr/bin/python
# Copyright 2013-2018 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import unittest
import shutil

import common_test
from config import GlobalConfig
from path import Path
from imagelogger import ImageLogger
from target import Image, Text, Pattern, Chain
from errors import *
from finder import *


class FinderTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.path = Path()
        self.path.add_path(os.path.join(common_test.unittest_dir, 'images'))

        # preserve values of static attributes
        self.prev_loglevel = GlobalConfig.image_logging_level
        self.prev_logpath = GlobalConfig.image_logging_destination
        self.prev_logwidth = GlobalConfig.image_logging_step_width

        self.logpath = os.path.join(common_test.unittest_dir, 'tmp')
        GlobalConfig.image_logging_level = 0
        GlobalConfig.image_logging_destination = self.logpath
        GlobalConfig.image_logging_step_width = 4

    @classmethod
    def tearDownClass(self):
        GlobalConfig.image_logging_level = self.prev_loglevel
        GlobalConfig.image_logging_destination = self.prev_logpath
        GlobalConfig.image_logging_step_width = self.prev_logwidth

    def setUp(self):
        # the image logger will recreate its logging destination
        ImageLogger.step = 1
        ImageLogger.accumulate_logging = False

    def tearDown(self):
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)

    def _get_matches_in(self, pattern, dumps):
        return [match.group(0) for d in dumps for match in [re.search(pattern, d)] if match]

    def _verify_and_get_dumps(self, count, index=1, multistep=False):
        dumps = os.listdir(self.logpath)
        self.assertEquals(len(dumps), count)
        steps = self._get_matches_in('imglog\d\d\d\d-.+', dumps)
        self.assertEquals(len(steps), len(dumps))
        first_steps = self._get_matches_in('imglog%04d-.+' % index, dumps)
        if not multistep:
            self.assertEquals(len(first_steps), len(steps))
        else:
            self.assertLessEqual(len(first_steps), len(steps))
        return dumps

    def _verify_dumped_images(self, needle_name, haystack_name, dumps, backend):
        needles = self._get_matches_in(".*needle.*", dumps)
        self.assertEquals(len(needles), 2)
        target, config = reversed(needles) if needles[0].endswith(".match") else needles
        self.assertIn("1needle", target)
        self.assertIn("1needle", config)
        self.assertIn(needle_name, target)
        self.assertIn(needle_name, config)
        self.assertTrue(config.endswith(".match"))
        self.assertEqual(os.path.splitext(target)[0], os.path.splitext(config)[0])
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, target)))
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, config)))
        with open(os.path.join(self.logpath, config)) as match_settings:
            self.assertIn("[find]\nbackend = %s" % backend, match_settings.read())

        haystacks = self._get_matches_in('.*haystack.*', dumps)
        self.assertEquals(len(haystacks), 1)
        haystack = haystacks[0]
        self.assertIn('2haystack', haystack)
        self.assertIn(haystack_name, haystack)
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, haystack)))

    def _verify_single_hotmap(self, dumps, backend):
        hotmaps = self._get_matches_in('.*hotmap.*', dumps)
        self.assertEquals(len(hotmaps), 1)
        self.assertIn('3hotmap', hotmaps[0])
        # report achieved similarity in the end of the filename
        self.assertRegexpMatches(hotmaps[0], ".*-\d\.\d+.*")
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[0])))

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_configure_backend(self):
        finder = Finder()
        finder.configure_backend("feature")
        self.assertEqual(finder.params["find"]["backend"], "feature")

        finder = AutoPyFinder()
        finder.configure()
        self.assertEqual(finder.params["find"]["backend"], "autopy")

        finder = TemplateFinder()
        finder.configure_backend("ccoeff_normed", reset=True)
        self.assertEqual(finder.params["find"]["backend"], "template")
        self.assertEqual(finder.params["template"]["backend"], "ccoeff_normed")

        finder = FeatureFinder()
        finder.configure()
        # test that a parameter of ORB (the current and default detector)
        # is present in parameters while a parameter of KAZE is not present
        self.assertTrue(finder.params["fdetect"].has_key("MaxFeatures"))
        self.assertFalse(finder.params["fdetect"].has_key("NOctaves"))

        finder = TemplateFeatureFinder()
        finder.configure(feature_detect="KAZE", feature_extract="ORB", feature_match="BruteForce")
        self.assertEqual(finder.params["find"]["backend"], "tempfeat")
        self.assertEqual(finder.params["template"]["backend"], "ccoeff_normed")
        self.assertEqual(finder.params["feature"]["backend"], "mixed")
        self.assertEqual(finder.params["fdetect"]["backend"], "KAZE")
        self.assertEqual(finder.params["fextract"]["backend"], "ORB")
        self.assertEqual(finder.params["fmatch"]["backend"], "BruteForce")

        # test that a parameter of KAZE (the new detector) is now present
        # while the parameter of ORB is not present anymore
        self.assertTrue(finder.params["fdetect"].has_key("NOctaves"))
        self.assertFalse(finder.params["fdetect"].has_key("MaxFeatures"))

        # check consistency of all unchanged options
        finder.configure_backend("ccorr_normed", "template")
        self.assertEqual(finder.params["find"]["backend"], "tempfeat")
        self.assertEqual(finder.params["template"]["backend"], "ccorr_normed")
        self.assertEqual(finder.params["feature"]["backend"], "mixed")
        self.assertEqual(finder.params["fdetect"]["backend"], "KAZE")
        self.assertEqual(finder.params["fextract"]["backend"], "ORB")
        self.assertEqual(finder.params["fmatch"]["backend"], "BruteForce")

        # check reset to defaults
        finder.configure(template_match="sqdiff_normed")
        self.assertEqual(finder.params["find"]["backend"], "tempfeat")
        self.assertEqual(finder.params["template"]["backend"], "sqdiff_normed")
        self.assertEqual(finder.params["feature"]["backend"], "mixed")
        self.assertEqual(finder.params["fdetect"]["backend"], "ORB")
        self.assertEqual(finder.params["fextract"]["backend"], "ORB")
        self.assertEqual(finder.params["fmatch"]["backend"], "BruteForce-Hamming")

    def test_autopy_same(self):
        finder = AutoPyFinder()
        finder.params["find"]["similarity"].value = 1.0
        matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 1)
        # AutoPy returns +1 pixel for both axes
        self.assertEqual(matches[0].x, 105)
        self.assertEqual(matches[0].y, 11)
        self.assertEqual(matches[0].width, 165)
        self.assertEqual(matches[0].height, 151)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(4)
        self._verify_dumped_images('shape_blue_circle', 'all_shapes', dumps, "autopy")
        self._verify_single_hotmap(dumps, "autopy")

    def test_autopy_nomatch(self):
        finder = AutoPyFinder()
        finder.params["find"]["similarity"].value = 0.25
        matches = finder.find(Image('n_ibs'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 0)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(4)
        self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "autopy")
        self._verify_single_hotmap(dumps, "autopy")

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_contour_same(self):
        finder = ContourFinder()
        # shape matching is not perfect
        finder.params["find"]["similarity"].value = 0.99
        i = 1

        for contour in finder.algorithms["contour_extractors"]:
            for threshold in finder.algorithms["threshold_filters"]:
                # TODO: this is still not implemented
                if contour == "components":
                    continue
                finder.configure_backend(contour, "contour")
                finder.configure_backend(threshold, "threshold")
                finder.params["contour"]["minArea"].value = 100
                matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))

                # verify match accuracy
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].x, 104)
                self.assertEqual(matches[0].y, 10)
                self.assertEqual(matches[0].width, 165)
                self.assertEqual(matches[0].height, 151)

                # verify dumped files count and names
                dumps = self._verify_and_get_dumps(6, i)
                self._verify_dumped_images('shape_blue_circle', 'all_shapes', dumps, "contour")
                hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
                self.assertEquals(len(hotmaps), 3)
                self.assertIn('3hotmap', hotmaps[0])
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmaps[0], ".*-\d\.\d+.*")
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[0])))
                self.assertIn('3hotmap-1threshold', hotmaps[1])
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[1])))
                self.assertIn('3hotmap-2contours', hotmaps[2])
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[1])))

                shutil.rmtree(self.logpath)
                i += 1

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_contour_nomatch(self):
        finder = ContourFinder()
        finder.params["find"]["similarity"].value = 0.25
        i = 1

        for contour in finder.algorithms["contour_extractors"]:
            for threshold in finder.algorithms["threshold_filters"]:
                finder.configure_backend(contour, "contour")
                finder.configure_backend(threshold, "threshold")
                finder.params["contour"]["minArea"].value = 100

                # verify match accuracy
                matches = finder.find(Image('n_ibs'), Image('all_shapes'))
                self.assertEqual(len(matches), 0)

                # verify dumped files count and names
                dumps = self._verify_and_get_dumps(6, i)
                self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "contour")
                hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
                self.assertEquals(len(hotmaps), 3)
                self.assertIn('3hotmap', hotmaps[0])
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmaps[0], ".*-\d\.\d+.*")
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[0])))
                self.assertIn('3hotmap-1threshold', hotmaps[1])
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[1])))
                self.assertIn('3hotmap-2contours', hotmaps[2])
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[1])))

                shutil.rmtree(self.logpath)
                i += 1

    def test_template_same(self):
        finder = TemplateFinder()
        finder.params["find"]["similarity"].value = 1.0
        i = 1

        for template in finder.algorithms["template_matchers"]:
            # one of the backend is not perfect for this case
            if template == "sqdiff_normed":
                finder.params["find"]["similarity"].value = 0.99
            finder.configure_backend(template, "template")
            matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))

            # verify match accuracy
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].x, 104)
            self.assertEqual(matches[0].y, 10)
            self.assertEqual(matches[0].width, 165)
            self.assertEqual(matches[0].height, 151)

            # verify dumped files count and names
            dumps = self._verify_and_get_dumps(5, i)
            self._verify_dumped_images('shape_blue_circle', 'all_shapes', dumps, "template")
            hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
            self.assertEquals(len(hotmaps), 2)
            for j, hotmap in enumerate(hotmaps):
                if j == 0:
                    self.assertIn('3hotmap', hotmap)
                else:
                    self.assertIn('3hotmap-1template', hotmap)
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

            shutil.rmtree(self.logpath)
            i += 1

    def test_template_nomatch(self):
        finder = TemplateFinder()
        finder.params["find"]["similarity"].value = 0.25
        i = 1

        for template in finder.algorithms["template_matchers"]:
            # one of the backend is too tolerant for this case
            if template == "ccorr_normed":
                continue
            finder.configure_backend(template, "template")
            matches = finder.find(Image('n_ibs'), Image('all_shapes'))

            # verify match accuracy
            self.assertEqual(len(matches), 0)

            # verify dumped files count and names
            dumps = self._verify_and_get_dumps(5, i)
            self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "template")
            hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
            self.assertEquals(len(hotmaps), 2)
            for j, hotmap in enumerate(hotmaps):
                if j == 0:
                    self.assertIn('3hotmap', hotmap)
                else:
                    self.assertIn('3hotmap-1template', hotmap)
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

            shutil.rmtree(self.logpath)
            i += 1

    def test_template_nocolor(self):
        finder = TemplateFinder()
        # template matching without color is not perfect
        finder.params["find"]["similarity"].value = 0.99

        for template in finder.algorithms["template_matchers"]:
            finder.configure_backend(template, "template")
            finder.params["template"]["nocolor"].value = True
            matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))

            # verify match accuracy
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].x, 104)
            self.assertEqual(matches[0].y, 10)
            self.assertEqual(matches[0].width, 165)
            self.assertEqual(matches[0].height, 151)

    def test_template_multiple(self):
        finder = TemplateFinder()
        finder.find(Image('shape_red_box'), Image('all_shapes'))

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(7)
        self._verify_dumped_images('shape_red_box', 'all_shapes', dumps, "template")
        hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
        self.assertEquals(len(hotmaps), 4)
        self.assertEquals(len(self._get_matches_in('.*3hotmap.*', hotmaps)), 4)
        for i, hotmap in enumerate(hotmaps):
            if i == 0:
                self.assertIn('3hotmap', hotmap)
            else:
                self.assertIn('3hotmap-%stemplate' % i, hotmap)
            # report achieved similarity in the end of the filename
            self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
            self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_feature_same(self):
        finder = FeatureFinder()
        finder.params["find"]["similarity"].value = 1.0
        i = 1

        for feature in finder.algorithms["feature_projectors"]:
            for fdetect in finder.algorithms["feature_detectors"]:
                for fextract in finder.algorithms["feature_extractors"]:
                    for fmatch in finder.algorithms["feature_matchers"]:
                        finder.configure_backend(feature, "feature")
                        finder.configure(feature_detect=fdetect,
                                         feature_extract=fextract,
                                         feature_match=fmatch)
                        # also with customized synchronization to the configuration
                        finder.synchronize_backend(feature, "feature")
                        finder.synchronize(feature_detect=fdetect,
                                           feature_extract=fextract,
                                           feature_match=fmatch)
                        matches = finder.find(Image('n_ibs'), Image('n_ibs'))

                        # verify match accuracy
                        self.assertEqual(len(matches), 1)
                        self.assertEqual(matches[0].x, 0)
                        self.assertEqual(matches[0].y, 0)
                        self.assertEqual(matches[0].width, 178)
                        self.assertEqual(matches[0].height, 269)

                        # verify dumped files count and names
                        dumps = self._verify_and_get_dumps(7, i)
                        self._verify_dumped_images('n_ibs', 'n_ibs', dumps, "feature")
                        hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
                        self.assertEquals(len(hotmaps), 4)
                        self.assertIn('3hotmap', hotmaps[0])
                        # report achieved similarity in the end of the filename
                        self.assertRegexpMatches(hotmaps[0], ".*-\d\.\d+.*")
                        self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[0])))
                        self.assertIn('3hotmap-1detect', hotmaps[1])
                        self.assertIn('3hotmap-2match', hotmaps[2])
                        self.assertIn('3hotmap-3project', hotmaps[3])

                        shutil.rmtree(self.logpath)
                        i += 1

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_feature_nomatch(self):
        finder = FeatureFinder()
        finder.params["find"]["similarity"].value = 0.25
        i = 1

        for feature in finder.algorithms["feature_projectors"]:
            for fdetect in finder.algorithms["feature_detectors"]:
                for fextract in finder.algorithms["feature_extractors"]:
                    for fmatch in finder.algorithms["feature_matchers"]:
                        finder.configure_backend(feature, "feature")
                        finder.configure(feature_detect=fdetect,
                                         feature_extract=fextract,
                                         feature_match=fmatch)
                        # also with customized synchronization to the configuration
                        finder.synchronize_backend(feature, "feature")
                        finder.synchronize(feature_detect=fdetect,
                                           feature_extract=fextract,
                                           feature_match=fmatch)
                        matches = finder.find(Image('n_ibs'), Image('all_shapes'))

                        # verify match accuracy
                        self.assertEqual(len(matches), 0)

                        # verify dumped files count and names
                        dumps = self._verify_and_get_dumps(7, i)
                        self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "feature")
                        hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
                        self.assertEquals(len(hotmaps), 4)
                        self.assertIn('3hotmap', hotmaps[0])
                        # report achieved similarity in the end of the filename
                        self.assertRegexpMatches(hotmaps[0], ".*-\d\.\d+.*")
                        self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[0])))
                        self.assertIn('3hotmap-1detect', hotmaps[1])
                        self.assertIn('3hotmap-2match', hotmaps[2])
                        self.assertIn('3hotmap-3project', hotmaps[3])

                        shutil.rmtree(self.logpath)
                        i += 1

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_feature_scaling(self):
        finder = FeatureFinder()
        finder.params["find"]["similarity"].value = 0.25
        matches = finder.find(Image('n_ibs'), Image('h_ibs_scaled'))
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 39, delta=5)
        self.assertAlmostEqual(matches[0].y, 222, delta=5)
        self.assertAlmostEqual(matches[0].width, 100, delta=10)
        self.assertAlmostEqual(matches[0].height, 150, delta=10)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_feature_rotation(self):
        finder = FeatureFinder()
        finder.params["find"]["similarity"].value = 0.45
        matches = finder.find(Image('n_ibs'), Image('h_ibs_rotated'))
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 435, delta=5)
        self.assertAlmostEqual(matches[0].y, 447, delta=5)
        self.assertAlmostEqual(matches[0].width, 270, delta=10)
        self.assertAlmostEqual(matches[0].height, 180, delta=10)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_feature_viewport(self):
        finder = FeatureFinder()
        finder.params["find"]["similarity"].value = 0.4
        matches = finder.find(Image('n_ibs'), Image('h_ibs_viewport'))
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 68, delta=5)
        self.assertAlmostEqual(matches[0].y, 18, delta=5)
        self.assertAlmostEqual(matches[0].width, 160, delta=10)
        self.assertAlmostEqual(matches[0].height, 235, delta=10)

    def test_cascade_same(self):
        finder = CascadeFinder()
        # no similarty parameter is supported - this is a binary match case
        finder.params["find"]["similarity"].value = 0.0
        matches = finder.find(Pattern('shape_blue_circle.xml'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 104, delta=5)
        self.assertAlmostEqual(matches[0].y, 10, delta=5)
        self.assertAlmostEqual(matches[0].width, 165, delta=10)
        self.assertAlmostEqual(matches[0].height, 151, delta=10)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(4)
        self._verify_dumped_images('shape_blue_circle', 'all_shapes', dumps, "cascade")
        self._verify_single_hotmap(dumps, "cascade")

    def test_cascade_nomatch(self):
        finder = CascadeFinder()
        # no similarty parameter is supported - this is a binary match case
        finder.params["find"]["similarity"].value = 0.0
        matches = finder.find(Pattern('n_ibs.xml'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 0)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(4)
        self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "cascade")
        self._verify_single_hotmap(dumps, "cascade")

    def test_cascade_scaling(self):
        finder = CascadeFinder()
        matches = finder.find(Pattern('n_ibs.xml'), Image('h_ibs_scaled'))
        self.assertEqual(len(matches), 1)
        # the original needle image was 150x150 with larger white margins
        self.assertAlmostEqual(matches[0].x, 10, delta=5)
        self.assertAlmostEqual(matches[0].y, 215, delta=5)
        # near square shape is due to the positive images used for training
        self.assertAlmostEqual(matches[0].width, 165, delta=5)
        self.assertAlmostEqual(matches[0].height, 165, delta=5)

    def test_cascade_rotation(self):
        finder = CascadeFinder()
        matches = finder.find(Pattern('n_ibs.xml'), Image('h_ibs_rotated'))
        # TODO: rotation does not work yet - increase angles in augmented data
        #self.assertEqual(len(matches), 1)
        #self.assertAlmostEqual(matches[0].x, 435, delta=5)
        #self.assertAlmostEqual(matches[0].y, 447, delta=5)
        #self.assertAlmostEqual(matches[0].width, 270, delta=10)
        #self.assertAlmostEqual(matches[0].height, 180, delta=10)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_cascade_viewport(self):
        finder = CascadeFinder()
        matches = finder.find(Pattern('n_ibs.xml'), Image('h_ibs_viewport'))
        self.assertEqual(len(matches), 1)
        # the original needle image was 150x150 with larger white margins
        self.assertAlmostEqual(matches[0].x, 20, delta=5)
        self.assertAlmostEqual(matches[0].y, 20, delta=5)
        # near square shape is due to the positive images used for training
        self.assertAlmostEqual(matches[0].width, 250, delta=10)
        self.assertAlmostEqual(matches[0].height, 250, delta=10)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_same(self):
        finder = TextFinder()
        finder.params["find"]["similarity"].value = 1.0
        i = 1

        for tdetect in finder.algorithms["text_detectors"]:
            # TODO: this is still not implemented
            if tdetect == "components":
                continue
            for ocr in finder.algorithms["text_recognizers"]:
                # TODO: this is still not implemented
                if ocr == "beamSearch":
                    continue

                # HMM misinterprets one char leading to 3/4 recognized chars
                # Tesseract still has similarity 1.0 though
                if ocr == "hmm":
                    finder.params["find"]["similarity"].value = 0.75
                else:
                    finder.params["find"]["similarity"].value = 1.0

                finder.configure_backend(tdetect, "tdetect")
                finder.configure_backend(ocr, "ocr")
                # also with customized synchronization to the configuration
                finder.synchronize_backend(tdetect, "tdetect")
                finder.synchronize_backend(ocr, "ocr")
                matches = finder.find(Text('Text'), Image('all_shapes'))

                # verify match accuracy
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].x, 22)
                self.assertEqual(matches[0].y, 83)
                self.assertAlmostEqual(matches[0].width, 40, delta=3)
                self.assertAlmostEqual(matches[0].height, 15, delta=3)

                # verify dumped files count and names
                dumps = self._verify_and_get_dumps(7, i)
                self._verify_dumped_images('Text', 'all_shapes', dumps, "text")
                hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
                self.assertEquals(len(hotmaps), 4)
                for j, hotmap in enumerate(hotmaps):
                    if j == 0:
                        self.assertIn('3hotmap', hotmap)
                    elif j == 1:
                        self.assertIn('3hotmap-1char', hotmap)
                    elif j == 2:
                        self.assertIn('3hotmap-2text', hotmap)
                    else:
                        self.assertIn('3hotmap-3ocr-%stext' % (j-2), hotmap)
                    if j == 3 or j == 4:
                        # report achieved similarity in the end of the filename
                        self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
                    self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

                shutil.rmtree(self.logpath)
                i += 1

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_nomatch(self):
        finder = TextFinder()
        finder.params["find"]["similarity"].value = 0.25
        i = 1

        for tdetect in finder.algorithms["text_detectors"]:
            # TODO: this is still not implemented
            if tdetect == "components":
                continue
            for ocr in finder.algorithms["text_recognizers"]:
                # TODO: this is still not implemented
                if ocr == "beamSearch":
                    continue
                finder.configure_backend(tdetect, "tdetect")
                finder.configure_backend(ocr, "ocr")
                # also with customized synchronization to the configuration
                finder.synchronize_backend(tdetect, "tdetect")
                finder.synchronize_backend(ocr, "ocr")
                matches = finder.find(Text('Nothing'), Image('all_shapes'))

                # verify match accuracy
                self.assertEqual(len(matches), 0)

                # verify dumped files count and names
                dumps = self._verify_and_get_dumps(7, i)
                self._verify_dumped_images('Nothing', 'all_shapes', dumps, "text")
                hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
                self.assertEquals(len(hotmaps), 4)
                for j, hotmap in enumerate(hotmaps):
                    if j == 0:
                        self.assertIn('3hotmap', hotmap)
                    elif j == 1:
                        self.assertIn('3hotmap-1char', hotmap)
                    elif j == 2:
                        self.assertIn('3hotmap-2text', hotmap)
                    else:
                        self.assertIn('3hotmap-3ocr-%stext' % (j-2), hotmap)
                    if j == 3 or j == 4:
                        # report achieved similarity in the end of the filename
                        self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
                    self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

                shutil.rmtree(self.logpath)
                i += 1

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_basic(self):
        finder = TextFinder()
        finder.params["find"]["similarity"].value = 0.7
        matches = finder.find(Text('Find the word here'), Image('sentence_sans'))
        self.assertEqual(len(matches), 1)
        # TODO: location too far due to poor text detection
        #self.assertEqual(matches[0].x, 11)
        self.assertEqual(matches[0].y, 12)
        self.assertAlmostEqual(matches[0].width, 110, delta=5)
        self.assertAlmostEqual(matches[0].height, 10, delta=5)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_bold(self):
        finder = TextFinder()
        finder.params["find"]["similarity"].value = 0.8
        matches = finder.find(Text('Find the word'), Image('sentence_bold'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].x, 12)
        self.assertEqual(matches[0].y, 13)
        self.assertAlmostEqual(matches[0].width, 100, delta=5)
        self.assertAlmostEqual(matches[0].height, 10, delta=5)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_italic(self):
        finder = TextFinder()
        finder.params["find"]["similarity"].value = 0.7
        matches = finder.find(Text('Find the word here'), Image('sentence_italic'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].x, 11)
        self.assertEqual(matches[0].y, 12)
        self.assertAlmostEqual(matches[0].width, 120, delta=5)
        self.assertAlmostEqual(matches[0].height, 10, delta=5)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_larger(self):
        finder = TextFinder()
        # TODO: this is too low to be a match (due to text detection)
        finder.params["find"]["similarity"].value = 0.4
        matches = finder.find(Text('Find the word'), Image('sentence_larger'))
        self.assertEqual(len(matches), 1)
        # TODO: location too far due to poor text detection
        #self.assertEqual(matches[0].x, 13)
        self.assertEqual(matches[0].y, 13)
        #self.assertAlmostEqual(matches[0].width, 100, delta=5)
        self.assertAlmostEqual(matches[0].height, 10, delta=5)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_text_font(self):
        finder = TextFinder()
        # TODO: this is too low to be a match
        finder.params["find"]["similarity"].value = 0.3
        matches = finder.find(Text('Find the word here'), Image('sentence_font'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].x, 7)
        self.assertEqual(matches[0].y, 13)
        self.assertAlmostEqual(matches[0].width, 120, delta=5)
        self.assertAlmostEqual(matches[0].height, 10, delta=5)

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_tempfeat_same(self):
        finder = TemplateFeatureFinder()
        finder.params["find"]["similarity"].value = 1.0
        i = 1

        for tempfeat in finder.algorithms["tempfeat_matchers"]:
            finder.configure_backend(tempfeat, "tempfeat")
            matches = finder.find(Image('n_ibs'), Image('n_ibs'))

            # verify match accuracy
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].x, 0)
            self.assertEqual(matches[0].y, 0)
            self.assertEqual(matches[0].width, 178)
            self.assertEqual(matches[0].height, 269)

            # verify dumped files count and names
            dumps = self._verify_and_get_dumps(6, i)
            self._verify_dumped_images('n_ibs', 'n_ibs', dumps, "tempfeat")
            hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
            self.assertEquals(len(hotmaps), 3)
            for i, hotmap in enumerate(hotmaps):
                if i == 0:
                    self.assertIn('3hotmap', hotmap)
                    self.assertNotIn('template', hotmap)
                    self.assertNotIn('feature', hotmap)
                elif i % 2 == 1:
                    self.assertIn('%sfeature' % ((i - 1) / 2 + 1), hotmap)
                else:
                    self.assertIn('%stemplate' % ((i - 1) / 2 + 1), hotmap)
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
                self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

            shutil.rmtree(self.logpath)
            i += 1

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1", "Old OpenCV version")
    def test_tempfeat_nomatch(self):
        finder = TemplateFeatureFinder()
        finder.params["find"]["similarity"].value = 0.25
        i = 1

        for tempfeat in finder.algorithms["tempfeat_matchers"]:
            finder.configure_backend(tempfeat, "tempfeat")
            matches = finder.find(Image('n_ibs'), Image('all_shapes'))

            # verify match accuracy
            self.assertEqual(len(matches), 0)

            # verify dumped files count and names
            dumps = self._verify_and_get_dumps(4, i)
            self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "tempfeat")
            hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
            self.assertEquals(len(hotmaps), 1)
            hotmap = hotmaps[0]
            self.assertIn('3hotmap', hotmap)
            self.assertNotIn('template', hotmap)
            self.assertNotIn('feature', hotmap)
            # report achieved similarity in the end of the filename
            self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
            self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

            shutil.rmtree(self.logpath)
            i += 1

    def test_deep_same(self):
        finder = DeepFinder()
        # shape matching is not perfect
        finder.params["find"]["similarity"].value = 0.99
        matches = finder.find(Pattern('shape_blue_circle.pth'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].x, 104)
        # TODO: need more precision to get y=10
        self.assertEqual(matches[0].y, 40)
        # based on a 15x15 output layer (network configuration)
        self.assertEqual(matches[0].width, Image('all_shapes').width/15)
        self.assertEqual(matches[0].height, Image('all_shapes').height/15)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(5)
        self._verify_dumped_images('shape_blue_circle', 'all_shapes', dumps, "deep")
        hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
        self.assertEquals(len(hotmaps), 2)
        for i, hotmap in enumerate(hotmaps):
            if i == 0:
                self.assertIn('3hotmap', hotmap)
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
            else:
                self.assertIn('%sactivity' % i, hotmap)
            self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

    def test_deep_nomatch(self):
        finder = DeepFinder()
        finder.params["find"]["similarity"].value = 0.25
        matches = finder.find(Pattern('n_ibs.pth'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 0)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(5)
        self._verify_dumped_images('n_ibs', 'all_shapes', dumps, "deep")
        hotmaps = sorted(self._get_matches_in('.*hotmap.*', dumps))
        self.assertEquals(len(hotmaps), 2)
        for i, hotmap in enumerate(hotmaps):
            if i == 0:
                self.assertIn('3hotmap', hotmap)
                # report achieved similarity in the end of the filename
                self.assertRegexpMatches(hotmap, ".*-\d\.\d+.*")
            else:
                self.assertIn('%sactivity' % i, hotmap)
            self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)))

    def test_hybrid_same(self):
        finder = HybridFinder()
        finder.configure_backend("autopy")
        finder.synchronize_backend("autopy")
        finder.params["find"]["similarity"].value = 1.0
        matches = finder.find(Chain('circle_simple'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 1)
        # AutoPy returns +1 pixel for both axes
        self.assertEqual(matches[0].x, 105)
        self.assertEqual(matches[0].y, 11)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(4)
        self._verify_dumped_images('shape_blue_circle', 'all_shapes', dumps, "autopy")
        self._verify_single_hotmap(dumps, "autopy")

    @unittest.skipIf(os.environ.get('LEGACY_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Old OpenCV version or disabled OCR functionality")
    def test_hybrid_nomatch(self):
        finder = HybridFinder()
        finder.configure_backend("autopy")
        finder.synchronize_backend("autopy")
        finder.params["find"]["similarity"].value = 1.0
        matches = finder.find(Chain('circle_fake'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 0)

        # verify dumped files count and names (4+4+7)
        dumps = self._verify_and_get_dumps(15, multistep=True)

    def test_hybrid_fallback(self):
        finder = HybridFinder()
        finder.configure_backend("autopy")
        finder.synchronize_backend("autopy")
        finder.params["find"]["similarity"].value = 1.0
        matches = finder.find(Chain('circle_fallback'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 1)
        # AutoPy returns +1 pixel for both axes
        self.assertEqual(matches[0].x, 105)
        self.assertEqual(matches[0].y, 11)

        # verify dumped files count and names
        dumps = self._verify_and_get_dumps(8, multistep=True)

    def test_hybrid_multiconfig(self):
        finder = HybridFinder()
        finder.configure_backend("autopy")
        finder.synchronize_backend("autopy")
        finder.params["find"]["similarity"].value = 1.0
        matches = finder.find(Chain('circle'), Image('all_shapes'))

        # verify match accuracy
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].x, 104)
        self.assertEqual(matches[0].y, 10)

        # verify dumped files count and names (+1 as we match with template)
        dumps = self._verify_and_get_dumps(9, multistep=True)

if __name__ == '__main__':
    unittest.main()