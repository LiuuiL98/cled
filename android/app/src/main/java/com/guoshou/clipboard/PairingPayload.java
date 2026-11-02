package com.guoshou.clipboard;

import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/** Validates the app-specific QR pairing payload. */
public final class PairingPayload {
    private PairingPayload() { }

    public static PairingInfo parse(String raw) {
        if (raw == null || raw.length() > 2048) return null;
        try {
            URI uri = URI.create(raw);
            if (!"guoshou-test".equals(uri.getScheme())
                    || !"pair".equals(uri.getHost())
                    || uri.getUserInfo() != null
                    || (uri.getPath() != null && !uri.getPath().isEmpty())
                    || uri.getFragment() != null) {
                return null;
            }

            Map<String, String> params = new HashMap<>();
            String query = uri.getRawQuery();
            if (query == null) return null;
            for (String item : query.split("&")) {
                String[] pair = item.split("=", 2);
                if (pair.length != 2) continue;
                String key = URLDecoder.decode(pair[0], StandardCharsets.UTF_8);
                String value = URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
                params.put(key, value);
            }

            String host = params.get("host");
            String portText = params.get("port");
            String token = params.get("token");
            if (!isPrivateIpv4(host) || !isHexToken(token)) return null;

            int port = Integer.parseInt(portText);
            if (port < 1 || port > 65535) return null;
            return new PairingInfo(host, port, token);
        } catch (RuntimeException ex) {
            return null;
        }
    }

    private static boolean isHexToken(String value) {
        return value != null && value.matches("[a-fA-F0-9]{64}");
    }

    private static boolean isPrivateIpv4(String host) {
        if (host == null || !host.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}")) return false;
        String[] parts = host.split("\\.");
        int[] octets = new int[4];
        for (int i = 0; i < parts.length; i++) {
            try {
                octets[i] = Integer.parseInt(parts[i]);
            } catch (NumberFormatException ex) {
                return false;
            }
            if (octets[i] < 0 || octets[i] > 255) return false;
        }
        return octets[0] == 10
                || (octets[0] == 192 && octets[1] == 168)
                || (octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31);
    }

    public static final class PairingInfo {
        public final String host;
        public final int port;
        public final String token;

        PairingInfo(String host, int port, String token) {
            this.host = host;
            this.port = port;
            this.token = token;
        }

        public String endpoint() {
            return host + ":" + port;
        }
    }
}
