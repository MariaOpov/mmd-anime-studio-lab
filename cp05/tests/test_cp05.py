"""Synthetic-only SDK permission tests; do not repeat CP01-CP04 suites."""
import json, unittest
from pathlib import Path
from unittest.mock import patch
from cp05.broker import PermissionBroker, KIND
from cp05.contract import negotiate, verify_contract, ContractHold, CONTRACT_SHA256
from cp05.cli import main
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

class CP05Tests(unittest.TestCase):
    def setUp(self): self.b=PermissionBroker()
    def grant(self,kind='morph'):
        ext,cap=KIND[kind]
        return self.b.grant(ext,cap)['token']
    def request(self,kind='morph',token=None):
        ext,cap=KIND[kind]
        return dict(sdk_version='0.1',kind=kind,extension_id=ext,capability=cap,
                    token=token,arguments={})
    def test_pinned_contract(self): self.assertEqual(verify_contract()['sdk_version'],'0.1')
    def test_sdk_valid(self): self.assertTrue(negotiate('0.1')['ok'])
    def test_sdk_rejects_new(self): self.assertFalse(negotiate('0.2')['ok'])
    def test_sdk_rejects_int(self): self.assertFalse(negotiate(0.1)['ok'])
    def test_sdk_rejects_bool(self): self.assertFalse(negotiate(True)['ok'])
    def test_contract_sha_length(self): self.assertEqual(len(CONTRACT_SHA256),64)
    def test_exact_four(self): self.assertEqual(len(self.b.catalog()['extensions']),4)
    def test_snapshot_no_write_network(self):
        x=self.b.catalog();self.assertEqual((x['real_assets'],x['writes'],x['network']),(False,False,False))
    def test_catalog_rejects_sdk(self): self.assertFalse(self.b.catalog('99')['ok'])
    def test_default_deny_all_four(self):
        for kind in KIND: self.assertEqual(self.b.execute(self.request(kind))['error'],'HOLD_PERMISSION_REQUIRED')
    def test_approve_all_four(self):
        for kind in KIND:
            token=self.grant(kind);self.assertTrue(self.b.execute(self.request(kind,token))['ok'])
    def test_grant_wrong_capability(self): self.assertFalse(self.b.grant(KIND['morph'][0],'read_motion')['ok'])
    def test_grant_unknown_id(self): self.assertFalse(self.b.grant('evil','read_model')['ok'])
    def test_grant_wrong_id_type(self): self.assertFalse(self.b.grant(14,'read_model')['ok'])
    def test_grant_wrong_cap_type(self): self.assertFalse(self.b.grant(KIND['pmx'][0],None)['ok'])
    def test_grant_wrong_sdk(self): self.assertFalse(self.b.grant(*KIND['pmx'],sdk_version='0.9')['ok'])
    def test_revoke(self):
        t=self.grant();self.assertTrue(self.b.revoke(t)['ok']);self.assertFalse(self.b.execute(self.request(token=t))['ok'])
    def test_revoke_invalid(self): self.assertFalse(self.b.revoke('no')['ok'])
    def test_token_not_cross_extension(self):
        t=self.grant();self.assertEqual(self.b.execute(self.request('motion',t))['error'],'HOLD_PERMISSION_REQUIRED')
    def test_token_not_cross_session(self):
        t=self.grant();self.assertFalse(PermissionBroker().execute(self.request(token=t))['ok'])
    def test_toggle_disabled_blocks_grant(self):
        e,c=KIND['morph'];self.assertTrue(self.b.set_enabled(e,False)['ok']);self.assertEqual(self.b.grant(e,c)['error'],'HOLD_EXTENSION_DISABLED')
    def test_toggle_clears_grants(self):
        e,c=KIND['morph'];t=self.grant();self.b.set_enabled(e,False);self.b.set_enabled(e,True);self.assertFalse(self.b.execute(self.request(token=t))['ok'])
    def test_toggle_unknown(self): self.assertFalse(self.b.set_enabled('bad',False)['ok'])
    def test_toggle_wrong_bool(self): self.assertFalse(self.b.set_enabled(KIND['morph'][0],1)['ok'])
    def test_execute_wrong_shape(self): self.assertEqual(self.b.execute([])['error'],'HOLD_REQUEST_SHAPE')
    def test_execute_path_denied(self):
        req=self.request('morph',self.grant());req['path']='C:/real.pmx';self.assertEqual(self.b.execute(req)['error'],'HOLD_REQUEST_SHAPE')
    def test_execute_arguments_path_denied(self):
        req=self.request('morph',self.grant());req['arguments']={'path':'C:/real.pmx'};self.assertEqual(self.b.execute(req)['error'],'HOLD_EXTERNAL_INPUT_NOT_ALLOWED')
    def test_execute_array_arguments_denied(self):
        req=self.request('morph',self.grant());req['arguments']=[];self.assertFalse(self.b.execute(req)['ok'])
    def test_execute_unknown_kind(self):
        req=self.request('morph');req['kind']='arbitrary';self.assertFalse(self.b.execute(req)['ok'])
    def test_execute_kind_type(self):
        req=self.request('morph');req['kind']=['morph'];self.assertFalse(self.b.execute(req)['ok'])
    def test_execute_version_denied(self):
        req=self.request('morph');req['sdk_version']='0.2';self.assertEqual(self.b.execute(req)['error'],'HOLD_UNSUPPORTED_SDK_VERSION')
    def test_execute_capability_mismatch(self):
        req=self.request('morph');req['capability']='read_model';self.assertFalse(self.b.execute(req)['ok'])
    def test_audit_no_secrets(self):
        t=self.grant();self.b.execute(self.request(token=t));self.assertNotIn(t,json.dumps(self.b.audit()))
    def test_audit_bounded(self):
        for _ in range(80): self.b.grant('untrusted','unknown')
        self.assertEqual(len(self.b.audit()),64)
    def test_audit_return_defensive_copy(self):
        self.b.grant('bad','bad');a=self.b.audit();a[0]['event']='alter';self.assertEqual(self.b.audit()[0]['event'],'GRANT_DENIED')
    def test_catalog_return_defensive_copy(self):
        self.b.catalog()['extensions'][0]['name']='forged';self.assertNotEqual(self.b.catalog()['extensions'][0]['name'],'forged')
    def test_cli_plugins(self):
        with redirect_stdout(StringIO()): self.assertEqual(main(['plugins']),0)
    def test_cli_morph(self):
        with redirect_stdout(StringIO()): self.assertEqual(main(['demo','morph']),0)
    def test_cli_motion(self):
        with redirect_stdout(StringIO()): self.assertEqual(main(['demo','motion']),0)
    def test_cli_deny_control(self):
        with redirect_stdout(StringIO()): self.assertEqual(main(['deny','morph']),0)
    def test_cli_filename_rejected(self):
        with redirect_stderr(StringIO()): self.assertEqual(main(['demo','C:/real.vmd']),4)
    def test_cli_unapproved_cmd_rejected(self):
        with redirect_stderr(StringIO()): self.assertEqual(main(['install','evil']),4)
    def test_studio_repo_not_imported(self):
        self.assertNotIn('mmd_registry',str(type(self.b.host)))
    def test_contract_tamper_denied(self):
        with patch('cp05.contract.CONTRACT_SHA256','0'*64):
            with self.assertRaises(ContractHold): verify_contract()
