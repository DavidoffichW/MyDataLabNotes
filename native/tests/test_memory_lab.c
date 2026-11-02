#include "mydatalabnotes/memory_lab.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
    return 1; \
} } while (0)

static int test_packet_known_vector(void) {
    const uint8_t expected[] = {
        0x4d, 0x44, 0x4c, 0x4e, 0x01, 0xa5, 0x01, 0x02, 0x03, 0x04,
        0xff, 0xff, 0xff, 0xfe, 0x11, 0x22, 0x00, 0x04, 0xde, 0xad,
        0xbe, 0xef
    };
    mdln_packet packet;
    mdln_packet decoded;
    uint8_t encoded[64];
    size_t length = 0U;
    memset(&packet, 0, sizeof(packet));
    packet.record_id = UINT32_C(0x01020304);
    packet.measurement_milli = -2;
    packet.sample_count = UINT16_C(0x1122);
    packet.flags = UINT8_C(0xa5);
    packet.payload_length = 4U;
    memcpy(packet.payload, expected + MDLN_PACKET_HEADER_SIZE, 4U);
    CHECK(mdln_packet_encode(&packet, encoded, sizeof(encoded), &length));
    CHECK(length == sizeof(expected));
    CHECK(memcmp(encoded, expected, sizeof(expected)) == 0);
    CHECK(mdln_packet_decode(encoded, length, &decoded));
    CHECK(decoded.record_id == packet.record_id);
    CHECK(decoded.measurement_milli == packet.measurement_milli);
    CHECK(decoded.sample_count == packet.sample_count);
    CHECK(decoded.flags == packet.flags);
    CHECK(decoded.payload_length == packet.payload_length);
    CHECK(memcmp(decoded.payload, packet.payload, packet.payload_length) == 0);
    CHECK(!mdln_packet_decode(encoded, length - 1U, &decoded));
    CHECK(!mdln_packet_decode(encoded, length + 1U, &decoded));
    encoded[16] = 0U;
    encoded[17] = 0U;
    CHECK(!mdln_packet_decode(encoded, MDLN_PACKET_HEADER_SIZE, &decoded));
    encoded[17] = 4U;
    encoded[0] = 0U;
    CHECK(!mdln_packet_decode(encoded, length, &decoded));
    return 0;
}

static int test_bounded_memory_history(void) {
    mdln_memory_lab lab;
    const uint8_t first[] = {1U, 2U, 3U, 4U};
    const uint8_t second[] = {0xaaU, 0xbbU};
    uint8_t unchanged[8];
    char trace_text[4096];
    size_t trace_length;
    FILE *trace = tmpfile();
    CHECK(trace != NULL);
    CHECK(mdln_lab_allocate(&lab, UINT64_C(7), 8U, 2U, trace));
    CHECK(mdln_lab_write(&lab, "write", 0U, first, sizeof(first)));
    CHECK(mdln_lab_write(&lab, "modify", 1U, second, sizeof(second)));
    CHECK(mdln_lab_copy(&lab, 0U, 4U, 4U));
    memcpy(unchanged, lab.bytes, sizeof(unchanged));
    CHECK(!mdln_lab_write(&lab, "write", 8U, first, 1U));
    CHECK(!mdln_lab_copy(&lab, 7U, 2U, 0U));
    CHECK(memcmp(unchanged, lab.bytes, sizeof(unchanged)) == 0);
    CHECK(mdln_lab_snapshot(&lab));
    CHECK(mdln_lab_release(&lab));
    CHECK(!mdln_lab_release(&lab));
    rewind(trace);
    trace_length = fread(trace_text, 1U, sizeof(trace_text) - 1U, trace);
    trace_text[trace_length] = '\0';
    CHECK(strstr(trace_text, "\"seq\":1") != NULL);
    CHECK(strstr(trace_text, "\"seq\":6") != NULL);
    CHECK(strstr(trace_text, "\"operation\":\"copy\"") != NULL);
    CHECK(strstr(trace_text, "\"operation\":\"release\"") != NULL);
    fclose(trace);
    return 0;
}

int main(void) {
    CHECK(test_packet_known_vector() == 0);
    CHECK(test_bounded_memory_history() == 0);
    puts("native memory laboratory tests passed");
    return 0;
}
