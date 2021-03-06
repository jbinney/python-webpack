import unittest
import os
import json
import mock
import hashlib
from webpack.conf import Conf
from webpack.manifest import generate_manifest, generate_key, write_manifest, read_manifest, populate_manifest_file
from webpack.compiler import webpack
from .settings import ConfigFiles, STATIC_ROOT, WEBPACK
from .utils import clean_static_root


class TestManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clean_static_root()

    @classmethod
    def tearDownClass(cls):
        clean_static_root()

    def test_a_manifest_key_is_relative(self):
        key = generate_key(ConfigFiles.BASIC_CONFIG)

        self.assertEqual(key, os.path.join('basic', 'webpack.config.js'))

    def test_a_manifest_key_contains_the_context(self):
        context = {'foo': 'bar'}

        key = generate_key(ConfigFiles.BASIC_CONFIG, context)
        hashed_context = hashlib.md5(json.dumps(context).encode('utf-8')).hexdigest()
        expected = os.path.join('basic', 'webpack.config.js') + '__' + hashed_context

        self.assertEqual(key, expected)

    def test_a_manifest_can_be_generated(self):
        manifest = generate_manifest(
            (ConfigFiles.BASIC_CONFIG,)
        )
        self.assertIsInstance(manifest, dict)
        self.assertEqual(len(manifest.keys()), 1)

        key = generate_key(ConfigFiles.BASIC_CONFIG)
        self.assertIn(key, manifest)
        entry = manifest[key]

        bundle = webpack(ConfigFiles.BASIC_CONFIG)
        self.assertEqual(entry, bundle.data)

    def test_a_manifest_can_be_generated_from_a_dictionary(self):
        manifest = generate_manifest({
            ConfigFiles.BASIC_CONFIG: ()
        })
        self.assertIsInstance(manifest, dict)
        self.assertEqual(len(manifest.keys()), 1)

        key = generate_key(ConfigFiles.BASIC_CONFIG)
        self.assertIn(key, manifest)
        entry = manifest[key]

        bundle = webpack(ConfigFiles.BASIC_CONFIG)
        self.assertEqual(entry, bundle.data)

    def test_a_manifest_can_be_generated_from_multiple_config_files(self):
        manifest = generate_manifest(
            (
                ConfigFiles.BASIC_CONFIG,
                ConfigFiles.LIBRARY_CONFIG,
            ),
        )
        self.assertIsInstance(manifest, dict)
        self.assertEqual(len(manifest.keys()), 2)

        key1 = generate_key(ConfigFiles.BASIC_CONFIG)
        self.assertIn(key1, manifest)
        entry1 = manifest[key1]

        bundle1 = webpack(ConfigFiles.BASIC_CONFIG)
        self.assertEqual(entry1, bundle1.data)

        key2 = generate_key(ConfigFiles.LIBRARY_CONFIG)
        self.assertIn(key2, manifest)
        entry2 = manifest[key2]

        bundle2 = webpack(ConfigFiles.LIBRARY_CONFIG)
        self.assertEqual(entry2, bundle2.data)

    def test_a_manifest_can_be_generated_from_multiple_config_files_in_a_dictionary(self):
        manifest = generate_manifest({
            ConfigFiles.BASIC_CONFIG: (),
            ConfigFiles.LIBRARY_CONFIG: (),
        })
        self.assertIsInstance(manifest, dict)
        self.assertEqual(len(manifest.keys()), 2)

        key1 = generate_key(ConfigFiles.BASIC_CONFIG)
        self.assertIn(key1, manifest)
        entry1 = manifest[key1]

        bundle1 = webpack(ConfigFiles.BASIC_CONFIG)
        self.assertEqual(entry1, bundle1.data)

        key2 = generate_key(ConfigFiles.LIBRARY_CONFIG)
        self.assertIn(key2, manifest)
        entry2 = manifest[key2]

        bundle2 = webpack(ConfigFiles.LIBRARY_CONFIG)
        self.assertEqual(entry2, bundle2.data)

    def test_a_manifest_can_be_generated_with_multiple_contexts(self):
        manifest = generate_manifest({
            ConfigFiles.BASIC_CONFIG: (
                {'foo': 'bar'},
            ),
            ConfigFiles.LIBRARY_CONFIG: (
                {'foo': 'bar'},
                {'woz': 'woo'},
            ),
        })
        self.assertIsInstance(manifest, dict)
        self.assertEqual(len(manifest.keys()), 3)

        key1 = generate_key(ConfigFiles.BASIC_CONFIG, {'foo': 'bar'})
        self.assertIn(key1, manifest)
        entry1 = manifest[key1]
        bundle1 = webpack(ConfigFiles.BASIC_CONFIG, context={'foo': 'bar'})
        self.assertEqual(entry1, bundle1.data)

        key2 = generate_key(ConfigFiles.LIBRARY_CONFIG, {'foo': 'bar'})
        self.assertIn(key2, manifest)
        entry2 = manifest[key2]
        bundle2 = webpack(ConfigFiles.LIBRARY_CONFIG, context={'foo': 'bar'})
        self.assertEqual(entry2, bundle2.data)

        key3 = generate_key(ConfigFiles.LIBRARY_CONFIG, {'woz': 'woo'})
        self.assertIn(key3, manifest)
        entry3 = manifest[key3]
        bundle3 = webpack(ConfigFiles.LIBRARY_CONFIG, context={'woz': 'woo'})
        self.assertEqual(entry3, bundle3.data)

    def test_a_manifest_can_be_written_to_and_read_from_disk(self):
        manifest = generate_manifest({
            ConfigFiles.BASIC_CONFIG: (
                {'foo': 'bar'},
            ),
            ConfigFiles.LIBRARY_CONFIG: (
                {'foo': 'bar'},
                {'woz': 'woo'},
            ),
        })

        path = os.path.join(STATIC_ROOT, 'foo.json')

        write_manifest(path, manifest)

        # Manual check
        with open(path, 'r') as manifest_file:
            content = manifest_file.read()
        self.assertEqual(json.loads(content), manifest)

        # Convenience check
        self.assertEqual(read_manifest(path), manifest)

    @staticmethod
    def _raise_if_called(*args, **kwargs):
        raise Exception('method called with args: {} and kwargs: {}'.format(args, kwargs))

    def test_the_manifest_is_used_by_the_compiler(self):
        manifest = generate_manifest({
            ConfigFiles.BASIC_CONFIG: (),
        })
        key = generate_key(ConfigFiles.BASIC_CONFIG)
        self.assertIn(key, manifest)

        path = os.path.join(STATIC_ROOT, 'test_manifest.json')
        write_manifest(path, manifest)

        with mock.patch('webpack.compiler.build_server.build', self._raise_if_called):
            mock_settings = Conf()
            mock_settings.configure(
                **dict(
                    WEBPACK,
                    USE_MANIFEST=True,
                    MANIFEST_PATH=path,
                )
            )

            with mock.patch('webpack.conf.settings', mock_settings):
                bundle = webpack(ConfigFiles.BASIC_CONFIG)
                self.assertEqual(bundle.data, manifest[key])

    def test_the_manifest_can_be_populated_from_settings(self):
        path = os.path.join(STATIC_ROOT, 'test_populate_manifest_file.json')

        mock_settings = Conf()
        mock_settings.configure(
            **dict(
                WEBPACK,
                USE_MANIFEST=True,
                MANIFEST_PATH=path,
                MANIFEST=(
                    ConfigFiles.BASIC_CONFIG,
                )
            )
        )

        with mock.patch('webpack.conf.settings', mock_settings):
            populate_manifest_file()

            with open(path, 'r') as manifest_file:
                content = manifest_file.read()
            manifest = json.loads(content)

            expected = generate_manifest(
                (ConfigFiles.BASIC_CONFIG,)
            )

            self.assertEqual(manifest, expected)

    def test_the_manifest_can_be_populated_from_a_dictionary(self):
        path = os.path.join(STATIC_ROOT, 'test_populate_dict_manifest_file.json')

        mock_settings = Conf()
        mock_settings.configure(
            **dict(
                WEBPACK,
                USE_MANIFEST=True,
                MANIFEST_PATH=path,
                MANIFEST={
                    ConfigFiles.BASIC_CONFIG: (),
                }
            )
        )

        with mock.patch('webpack.conf.settings', mock_settings):
            populate_manifest_file()

            with open(path, 'r') as manifest_file:
                content = manifest_file.read()
            manifest = json.loads(content)

            expected = generate_manifest({
                ConfigFiles.BASIC_CONFIG: (),
            })

            self.assertEqual(manifest, expected)