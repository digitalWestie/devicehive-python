# -*- encoding: utf8 -*-
# vim: set et tabstop=4 shiftwidth=4 nu nowrap: fileencoding=utf-8 encoding=utf-8

import sys
from os import path
import unittest


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..')))
try :
    binary_module = __import__('binary')
    globals().update(vars(binary_module))
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.pkt = Packet(PACKET_SIGNATURE, 2, 3, 4, bytearray('123'))
    
    def tearDown(self):
        pass
    
    def test_properties(self):
        self.assertEquals(PACKET_SIGNATURE, self.pkt.signature, 'Signatures are not equal')
        self.assertEquals(2, self.pkt.version, 'Versions are not equal')
        self.assertEquals(3, self.pkt.flags, 'Flags are not equal')
        self.assertEquals(4, self.pkt.intent, 'Intents are not equal')
    
    def test_checksum(self):
        self.assertEquals(0xd5, self.pkt.checksum, 'Invalid checksum')
    
    def test_to_binary(self):
        tstval = bytearray([PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5])
        binval = self.pkt.to_binary()
        self.assertEquals(tstval, binval, 'Invalid binary message has been formated')
    
    def test_from_binary(self):
        pktcopy = Packet.from_binary(self.pkt.to_binary())
        self.assertEquals(self.pkt.signature, pktcopy.signature)
        self.assertEquals(self.pkt.version, pktcopy.version)
        self.assertEquals(self.pkt.flags, pktcopy.flags)
        self.assertEquals(self.pkt.intent, pktcopy.intent)
        self.assertEquals(self.pkt.length, pktcopy.length)
        self.assertEquals(self.pkt.data, pktcopy.data)

    def test_crc_error(self):
        tstval = bytearray([PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xBA])
        try:
           Packet.from_binary(tstval)
           self.assertTrue(False, 'from_binary method should raises InvalidCRCError')
        except InvalidCRCError:
            pass
    
    def test_incomplete_packet(self):
        tstval = bytearray([0, 1, 2, 3])
        try:
            Packet.from_binary(tstval)
            self.assertTrue(False, 'from_binary method should raises IncompltePacketError in case data-packet passed into this method is too small')
        except IncompletePacketError:
            pass
    
    def test_invalid_packet_length(self):
        tstval = bytearray([PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x00, 0x03, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5])
        try:
            Packet.from_binary(tstval)
            self.assertTrue(False, 'from_binary method should raises InvalidPacketlengthError in case there not enough data passed into it')
        except InvalidPacketLengthError:
            pass
    
    def test_raise_invalid_signature(self):
        tstval = bytearray([0xBA, 0xD1, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5])
        try:
            Packet.from_binary(tstval)
            self.assertTrue(False, 'from_binary method should raises InvalidSignatureError in case packet signature is incorrect')
        except InvalidSignatureError:
            pass


class BinaryPacketBufferTests(unittest.TestCase):
    def test_adding_normal_packet(self):
        pkt = [PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff  = BinaryPacketBuffer()
        pkt_buff.append(pkt)
        self.assertEquals(pkt, pkt_buff.data)
        self.assertTrue(pkt_buff.has_packet())
    
    def test_adding_partial_packet(self):
        pkt = [PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff  = BinaryPacketBuffer()
        pkt_buff.append(pkt[:4])
        pkt_buff.append(pkt[4:])
        self.assertEquals(pkt, pkt_buff.data, 'One complete packet should be located in the buffer')
        self.assertTrue(pkt_buff.has_packet())
    
    def test_add_packet_prefixed_with_junk(self):
        pkt = [0xBA, 0xDB, 0xAD, PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append(pkt[:6])
        pkt_buff.append(pkt[6:])
        self.assertEquals(pkt[3:], pkt_buff.data, 'Junk data should be skipped in the head of packet buffer')
        self.assertTrue(pkt_buff.has_packet())

    def test_onechar_junk_add(self):
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append([0])
        pkt_buff.append([1])
        pkt_buff.append([2])
        self.assertEquals(0, len(pkt_buff.data), 'If buffer is empty and one character comes to it this character should be of SIGNATURE_HI value')
        self.assertFalse(pkt_buff.has_packet())

    def test_invalid_signature(self):
        pkt = [99, 98, 97, PACKET_SIGNATURE_HI, 96, PACKET_SIGNATURE_LO, 94, 93, PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append(pkt)
        self.assertEquals(pkt[8:], pkt_buff.data, 'Buffer should starts from FULL frame signature')
        self.assertTrue(pkt_buff.has_packet())
    
    def test_inv_sign_last_signhi(self):
        pkt = [99, 98, 97, PACKET_SIGNATURE_HI, 96, PACKET_SIGNATURE_LO, 94, 93, PACKET_SIGNATURE_HI]
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append(pkt)
        self.assertEquals([PACKET_SIGNATURE_HI], pkt_buff.data, 'One last character should stay untoched if it is SIGNATURE_HI')
        self.assertFalse(pkt_buff.has_packet())
    
    def test_signature_byteatatime(self):
        pkt = [99, 98, 97, PACKET_SIGNATURE_HI, 96, PACKET_SIGNATURE_LO, 94, 93, PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff = BinaryPacketBuffer()
        for byte in pkt:
            pkt_buff.append([byte])
        self.assertEquals(pkt[8:], pkt_buff.data, 'Even if we adds packet by one byte the buffer should starts from FULL frame signature')
        self.assertTrue(pkt_buff.has_packet())


class _SubObject(object):
    def __init__(self, val = 0):
        self._val = val
    def _set_val(self, value):
        self._val = value
    sword_prop = binary_property(DataTypes.SignedWord, fget = lambda self : self._val, fset = _set_val)
    __binary_struct__ = [sword_prop]


class _TestObject(object):
    def __init__(self):
        self._byte_prop = 0
        self._word_prop = 0
        self._dword_prop = 0
        self._bool_prop = False
        self._false_prop = False
        self._str_prop = ''
        self.arr_prop = []
        self.guid_prop = uuid.uuid1()
        self.aguid_prop = (uuid.uuid1()).bytes
    def gen_props(name):
        def fget(self):
            return getattr(self, name)
        def fset(self, value):
            setattr(self, name, value)
        return {'fget': fget, 'fset': fset}
    byte_prop  = binary_property(DataTypes.Byte, **gen_props('_byte_prop'))
    word_prop  = binary_property(DataTypes.Word, **gen_props('_word_prop'))
    dword_prop = binary_property(DataTypes.Dword, **gen_props('_dword_prop'))
    bool_prop  = binary_property(DataTypes.Boolean, **gen_props('_bool_prop'))
    false_prop = binary_property(DataTypes.Boolean, **gen_props('_false_prop'))
    str_prop   = binary_property(DataTypes.String, **gen_props('_str_prop'))
    arr_prop   = array_binary_property(_SubObject, **gen_props('_arr_prop'))
    guid_prop  = binary_property(DataTypes.Guid, **gen_props('_guid_prop'))
    aguid_prop = binary_property(DataTypes.Guid, **gen_props('_aguid_prop'))
    __binary_struct__ = (byte_prop, word_prop, dword_prop, bool_prop, false_prop, str_prop, arr_prop, guid_prop, aguid_prop)


class BinaryFormatterTest(unittest.TestCase):
    def _create_default_test_object(self):
        res = _TestObject()
        res.byte_prop  = 0xab
        res.word_prop  = 0xabcd
        res.dword_prop = 0x12345678
        res.bool_prop  = True
        res.false_prop = False
        res.str_prop   = 'abc'
        res.arr_prop   = [_SubObject(-1024), _SubObject(-8192)]
        res.guid_prop  = uuid.UUID('fa8a9d6e-6555-11e2-89b8-e0cb4eb92129')
        res.aguid_prop = res.guid_prop.bytes
        return res
    
    def setUp(self):
        self.binary = bytearray([0xab,
                                 0xcd, 0xab,
                                 0x78, 0x56, 0x34, 0x12,
                                 0x01,
                                 0x00,
                                 0x03, 0x00, ord('a'), ord('b'), ord('c'),
                                 0x02, 0x00, 0x00, 0xfc, 0x00, 0xe0,
                                 0xfa, 0x8a, 0x9d, 0x6e, 0x65, 0x55, 0x11, 0xe2, 0x89, 0xb8, 0xe0, 0xcb, 0x4e, 0xb9, 0x21, 0x29,
                                 0xfa, 0x8a, 0x9d, 0x6e, 0x65, 0x55, 0x11, 0xe2, 0x89, 0xb8, 0xe0, 0xcb, 0x4e, 0xb9, 0x21, 0x29])
    
    def test_serialize_byte(self):
        obj = self._create_default_test_object()
        binstr = BinaryFormatter.serialize(obj)
        self.assertEquals(self.binary, binstr)
    
    def test_deserializer(self):
        res = BinaryFormatter.deserialize(self.binary, _TestObject)
        self.assertEquals(0xab, res.byte_prop)
        self.assertEquals(0xabcd, res.word_prop)
        self.assertEquals(0x12345678, res.dword_prop)
        self.assertTrue(res.bool_prop)
        self.assertFalse(res.false_prop)
        self.assertEquals('abc', res.str_prop)
        self.assertEquals(2, len(res.arr_prop))
        self.assertEquals(-1024, res.arr_prop[0].sword_prop)
        self.assertEquals(-8192, res.arr_prop[1].sword_prop)
        
        guid = uuid.UUID('fa8a9d6e-6555-11e2-89b8-e0cb4eb92129')
        self.assertEquals(guid, res.guid_prop)
        self.assertEquals(guid, res.aguid_prop)


class AutoClassFactoryTest(unittest.TestCase):
    def test_auto_class(self):
        params = (Parameter(DataTypes.Word, 'property1'), Parameter(DataTypes.Byte, 'property2'))
        cmd = Command(intent = 100, name = 'CommandName', parameters = params)
        #
        factory = AutoClassFactory()
        cls = factory.generate(cmd)
        self.assertTrue(hasattr(cls, 'property1'))
        self.assertTrue(isinstance(cls.property1, AbstractBinaryProperty))
        self.assertTrue(hasattr(cls, 'property2'))
        self.assertTrue(isinstance(cls.property2, AbstractBinaryProperty))
        #
        obj = cls()
        autoclass_update_properties(obj, {'property1': 123, 'property2': 321})
        self.assertEquals(123, obj.property1)
        self.assertEquals(321, obj.property2)

if __name__ == '__main__':
    unittest.main()
