package com.guoshou.clipboard;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

public class PairingPayloadTest {
    private static final String TOKEN = "a".repeat(64);

    @Test
    public void parsesValidPrivateLanPairingCode() {
        PairingPayload.PairingInfo info = PairingPayload.parse(
            "guoshou-test://pair?host=192.168.1.23&port=8765&token=" + TOKEN);
        assertEquals("192.168.1.23", info.host);
        assertEquals(8765, info.port);
        assertEquals(TOKEN, info.token);
    }

    @Test
    public void rejectsWrongSchemeAndPublicIp() {
        assertNull(PairingPayload.parse(
            "https://pair?host=192.168.1.23&port=8765&token=" + TOKEN));
        assertNull(PairingPayload.parse(
            "guoshou-test://pair?host=8.8.8.8&port=8765&token=" + TOKEN));
    }

    @Test
    public void rejectsInvalidPortOrToken() {
        assertNull(PairingPayload.parse(
            "guoshou-test://pair?host=192.168.1.23&port=70000&token=" + TOKEN));
        assertNull(PairingPayload.parse(
            "guoshou-test://pair?host=192.168.1.23&port=8765&token=bad"));
    }
}
