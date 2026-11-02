#include "mydatalabnotes/memory_lab.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_OPERATIONS 64
#define MAX_OPERATION_TEXT 1024

static bool parse_u64(const char *text, uint64_t maximum, uint64_t *value) {
    char *end = NULL;
    unsigned long long parsed;
    if (text == NULL || text[0] == '\0' || text[0] == '-' || text[0] == '+') {
        return false;
    }
    errno = 0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed > maximum) {
        return false;
    }
    *value = (uint64_t)parsed;
    return true;
}

static int hex_digit(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
    if (value >= 'A' && value <= 'F') return value - 'A' + 10;
    return -1;
}

static bool parse_hex(const char *text, uint8_t *output, size_t maximum,
                      size_t *length) {
    size_t text_length = strlen(text);
    size_t index;
    if (text_length == 0U || text_length % 2U != 0U || text_length / 2U > maximum) {
        return false;
    }
    for (index = 0U; index < text_length / 2U; ++index) {
        int high = hex_digit(text[index * 2U]);
        int low = hex_digit(text[index * 2U + 1U]);
        if (high < 0 || low < 0) return false;
        output[index] = (uint8_t)((high << 4) | low);
    }
    *length = text_length / 2U;
    return true;
}

static void print_hex(const uint8_t *bytes, size_t length) {
    size_t index;
    for (index = 0U; index < length; ++index) printf("%02x", bytes[index]);
}

static int packet_command(int argc, char **argv) {
    mdln_packet packet;
    mdln_packet decoded;
    uint8_t encoded[MDLN_PACKET_HEADER_SIZE + MDLN_PACKET_MAX_PAYLOAD];
    uint64_t value;
    size_t encoded_length = 0U;
    size_t payload_length = 0U;
    if (argc != 7) return 2;
    memset(&packet, 0, sizeof(packet));
    if (!parse_u64(argv[2], UINT32_MAX, &value)) return 2;
    packet.record_id = (uint32_t)value;
    {
        char *end = NULL;
        long parsed;
        errno = 0;
        parsed = strtol(argv[3], &end, 10);
        if (errno != 0 || end == argv[3] || *end != '\0' ||
            parsed < INT32_MIN || parsed > INT32_MAX) return 2;
        packet.measurement_milli = (int32_t)parsed;
    }
    if (!parse_u64(argv[4], UINT16_MAX, &value)) return 2;
    packet.sample_count = (uint16_t)value;
    if (!parse_u64(argv[5], UINT8_MAX, &value)) return 2;
    packet.flags = (uint8_t)value;
    if (!parse_hex(argv[6], packet.payload, MDLN_PACKET_MAX_PAYLOAD,
                   &payload_length)) return 2;
    packet.payload_length = (uint8_t)payload_length;
    if (!mdln_packet_encode(&packet, encoded, sizeof(encoded), &encoded_length) ||
        !mdln_packet_decode(encoded, encoded_length, &decoded)) return 3;
    printf("{\"schema\":\"mydatalabnotes.packet.v1\",\"portable_hex\":\"");
    print_hex(encoded, encoded_length);
    printf("\",\"record_id\":%" PRIu32 ",\"measurement_milli\":%" PRId32
           ",\"sample_count\":%" PRIu16 ",\"flags\":%u,\"payload_hex\":\"",
           decoded.record_id, decoded.measurement_milli, decoded.sample_count,
           (unsigned)decoded.flags);
    print_hex(decoded.payload, decoded.payload_length);
    fputs("\"}\n", stdout);
    return 0;
}

static bool execute_operation(mdln_memory_lab *lab, const char *text) {
    char copy[MAX_OPERATION_TEXT];
    char *kind;
    char *first;
    char *second;
    char *third;
    uint64_t value_a;
    uint64_t value_b;
    uint64_t value_c;
    uint8_t bytes[MDLN_LAB_MAX_BYTES];
    size_t byte_count;
    size_t length = strlen(text);
    if (length == 0U || length >= sizeof(copy)) return false;
    memcpy(copy, text, length + 1U);
    kind = strtok(copy, ":");
    first = strtok(NULL, ":");
    second = strtok(NULL, ":");
    third = strtok(NULL, ":");
    if (strcmp(kind, "snapshot") == 0 && first == NULL) return mdln_lab_snapshot(lab);
    if (strcmp(kind, "release") == 0 && first == NULL) return mdln_lab_release(lab);
    if ((strcmp(kind, "write") == 0 || strcmp(kind, "modify") == 0) &&
        first != NULL && second != NULL && third == NULL &&
        parse_u64(first, MDLN_LAB_MAX_BYTES, &value_a) &&
        parse_hex(second, bytes, sizeof(bytes), &byte_count)) {
        return mdln_lab_write(lab, kind, (size_t)value_a, bytes, byte_count);
    }
    if (strcmp(kind, "copy") == 0 && first != NULL && second != NULL &&
        third != NULL && strtok(NULL, ":") == NULL &&
        parse_u64(first, MDLN_LAB_MAX_BYTES, &value_a) &&
        parse_u64(second, MDLN_LAB_MAX_BYTES, &value_b) &&
        parse_u64(third, MDLN_LAB_MAX_BYTES, &value_c)) {
        return mdln_lab_copy(lab, (size_t)value_a, (size_t)value_b,
                             (size_t)value_c);
    }
    return false;
}

static int trace_command(int argc, char **argv) {
    mdln_memory_lab lab;
    uint64_t allocation_id;
    uint64_t capacity;
    uint64_t checkpoint_interval;
    int index;
    if (argc < 6 || argc - 5 > MAX_OPERATIONS ||
        !parse_u64(argv[2], UINT64_MAX, &allocation_id) || allocation_id == 0U ||
        !parse_u64(argv[3], MDLN_LAB_MAX_BYTES, &capacity) || capacity == 0U ||
        !parse_u64(argv[4], MDLN_LAB_MAX_BYTES, &checkpoint_interval) ||
        !mdln_lab_allocate(&lab, allocation_id, (size_t)capacity,
                           (size_t)checkpoint_interval, stdout)) return 2;
    for (index = 5; index < argc; ++index) {
        if (!execute_operation(&lab, argv[index])) {
            if (lab.live) (void)mdln_lab_release(&lab);
            fprintf(stderr, "operation %d rejected\n", index - 4);
            return 3;
        }
    }
    if (lab.live) (void)mdln_lab_release(&lab);
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 2 && strcmp(argv[1], "layout") == 0 && argc == 2) {
        mdln_print_layout_json(stdout);
        return 0;
    }
    if (argc >= 2 && strcmp(argv[1], "packet") == 0) return packet_command(argc, argv);
    if (argc >= 2 && strcmp(argv[1], "trace") == 0) return trace_command(argc, argv);
    fputs("usage: memory_lab layout | packet ID MILLI COUNT FLAGS PAYLOAD_HEX | "
          "trace ALLOCATION_ID CAPACITY CHECKPOINT_INTERVAL OP...\n", stderr);
    return 2;
}
