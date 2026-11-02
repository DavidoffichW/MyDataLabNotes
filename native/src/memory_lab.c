#include "mydatalabnotes/memory_lab.h"

#include <inttypes.h>
#include <limits.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t PACKET_MAGIC[MDLN_PACKET_MAGIC_SIZE] = {'M', 'D', 'L', 'N'};
static const uint8_t PACKET_VERSION = 1U;

static void put_u16_be(uint8_t *output, uint16_t value) {
    output[0] = (uint8_t)(value >> 8U);
    output[1] = (uint8_t)value;
}

static void put_u32_be(uint8_t *output, uint32_t value) {
    output[0] = (uint8_t)(value >> 24U);
    output[1] = (uint8_t)(value >> 16U);
    output[2] = (uint8_t)(value >> 8U);
    output[3] = (uint8_t)value;
}

static uint16_t get_u16_be(const uint8_t *input) {
    return (uint16_t)(((uint16_t)input[0] << 8U) | (uint16_t)input[1]);
}

static uint32_t get_u32_be(const uint8_t *input) {
    return ((uint32_t)input[0] << 24U) | ((uint32_t)input[1] << 16U) |
           ((uint32_t)input[2] << 8U) | (uint32_t)input[3];
}

size_t mdln_packet_wire_size(const mdln_packet *packet) {
    if (packet == NULL || packet->payload_length > MDLN_PACKET_MAX_PAYLOAD) {
        return 0U;
    }
    return MDLN_PACKET_HEADER_SIZE + (size_t)packet->payload_length;
}

bool mdln_packet_encode(const mdln_packet *packet, uint8_t *output,
                        size_t output_capacity, size_t *output_length) {
    const size_t required = mdln_packet_wire_size(packet);
    if (required == 0U || output == NULL || output_length == NULL ||
        output_capacity < required) {
        return false;
    }
    memcpy(output, PACKET_MAGIC, MDLN_PACKET_MAGIC_SIZE);
    output[4] = PACKET_VERSION;
    output[5] = packet->flags;
    put_u32_be(output + 6U, packet->record_id);
    put_u32_be(output + 10U, (uint32_t)packet->measurement_milli);
    put_u16_be(output + 14U, packet->sample_count);
    put_u16_be(output + 16U, packet->payload_length);
    memcpy(output + MDLN_PACKET_HEADER_SIZE, packet->payload,
           packet->payload_length);
    *output_length = required;
    return true;
}

bool mdln_packet_decode(const uint8_t *input, size_t input_length,
                        mdln_packet *packet) {
    uint16_t payload_length;
    if (input == NULL || packet == NULL || input_length < MDLN_PACKET_HEADER_SIZE ||
        memcmp(input, PACKET_MAGIC, MDLN_PACKET_MAGIC_SIZE) != 0 ||
        input[4] != PACKET_VERSION) {
        return false;
    }
    payload_length = get_u16_be(input + 16U);
    if (payload_length == 0U || payload_length > MDLN_PACKET_MAX_PAYLOAD ||
        input_length != MDLN_PACKET_HEADER_SIZE + (size_t)payload_length) {
        return false;
    }
    memset(packet, 0, sizeof(*packet));
    packet->flags = input[5];
    packet->record_id = get_u32_be(input + 6U);
    {
        const uint32_t raw_measurement = get_u32_be(input + 10U);
        packet->measurement_milli = raw_measurement <= INT32_MAX
            ? (int32_t)raw_measurement
            : -(int32_t)(UINT32_MAX - raw_measurement) - 1;
    }
    packet->sample_count = get_u16_be(input + 14U);
    packet->payload_length = (uint8_t)payload_length;
    memcpy(packet->payload, input + MDLN_PACKET_HEADER_SIZE, payload_length);
    return true;
}

uint64_t mdln_fnv1a64(const uint8_t *bytes, size_t length) {
    uint64_t hash = UINT64_C(14695981039346656037);
    size_t index;
    for (index = 0U; index < length; ++index) {
        hash ^= (uint64_t)bytes[index];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static void print_hex(FILE *output, const uint8_t *bytes, size_t length) {
    size_t index;
    for (index = 0U; index < length; ++index) {
        fprintf(output, "%02x", bytes[index]);
    }
}

static bool range_is_valid(const mdln_memory_lab *lab, size_t offset,
                           size_t length) {
    return lab != NULL && lab->live && offset <= lab->capacity &&
           length <= lab->capacity - offset;
}

static void emit_event(mdln_memory_lab *lab, const char *operation, size_t offset,
                       size_t length, size_t source_offset,
                       const uint8_t *before, const uint8_t *after,
                       bool force_checkpoint) {
    const bool checkpoint = lab->live &&
        (force_checkpoint || lab->sequence == 1U ||
         (lab->checkpoint_interval > 0U &&
          lab->sequence % lab->checkpoint_interval == 0U));
    const uint64_t fingerprint = mdln_fnv1a64(
        lab->live ? lab->bytes : NULL, lab->live ? lab->capacity : 0U);
    fprintf(lab->trace,
            "{\"schema\":\"mydatalabnotes.memory-event.v1\","
            "\"seq\":%" PRIu64 ",\"allocation_id\":%" PRIu64
            ",\"operation\":\"%s\",\"offset\":%" PRIu64
            ",\"length\":%" PRIu64 ",\"source_offset\":%" PRIu64
            ",\"before_hex\":\"",
            lab->sequence, lab->allocation_id, operation, (uint64_t)offset,
            (uint64_t)length, (uint64_t)source_offset);
    print_hex(lab->trace, before, before == NULL ? 0U : length);
    fputs("\",\"after_hex\":\"", lab->trace);
    print_hex(lab->trace, after, after == NULL ? 0U : length);
    fputs("\",\"checkpoint_hex\":\"", lab->trace);
    if (checkpoint) {
        print_hex(lab->trace, lab->bytes, lab->capacity);
    }
    fputs("\",\"reference_state_hex\":\"", lab->trace);
    if (lab->live) {
        print_hex(lab->trace, lab->bytes, lab->capacity);
    }
    fprintf(lab->trace,
            "\",\"live\":%s,\"state_fingerprint\":\"%016" PRIx64
            "\"}\n",
            lab->live ? "true" : "false", fingerprint);
}

bool mdln_lab_allocate(mdln_memory_lab *lab, uint64_t allocation_id,
                       size_t capacity, size_t checkpoint_interval, FILE *trace) {
    if (lab == NULL || trace == NULL || allocation_id == 0U || capacity == 0U ||
        capacity > MDLN_LAB_MAX_BYTES) {
        return false;
    }
    memset(lab, 0, sizeof(*lab));
    lab->bytes = calloc(capacity, sizeof(uint8_t));
    if (lab->bytes == NULL) {
        return false;
    }
    lab->capacity = capacity;
    lab->allocation_id = allocation_id;
    lab->checkpoint_interval = checkpoint_interval;
    lab->live = true;
    lab->trace = trace;
    lab->sequence = 1U;
    emit_event(lab, "allocate", 0U, capacity, 0U, NULL, lab->bytes, true);
    return true;
}

bool mdln_lab_write(mdln_memory_lab *lab, const char *operation, size_t offset,
                    const uint8_t *bytes, size_t length) {
    uint8_t before[MDLN_LAB_MAX_BYTES];
    if (!range_is_valid(lab, offset, length) || operation == NULL || bytes == NULL ||
        length == 0U ||
        (strcmp(operation, "write") != 0 && strcmp(operation, "modify") != 0)) {
        return false;
    }
    memcpy(before, lab->bytes + offset, length);
    memcpy(lab->bytes + offset, bytes, length);
    lab->sequence += 1U;
    emit_event(lab, operation, offset, length, 0U, before,
               lab->bytes + offset, false);
    return true;
}

bool mdln_lab_copy(mdln_memory_lab *lab, size_t source_offset, size_t length,
                   size_t destination_offset) {
    uint8_t before[MDLN_LAB_MAX_BYTES];
    if (!range_is_valid(lab, source_offset, length) ||
        !range_is_valid(lab, destination_offset, length) || length == 0U) {
        return false;
    }
    memcpy(before, lab->bytes + destination_offset, length);
    memmove(lab->bytes + destination_offset, lab->bytes + source_offset, length);
    lab->sequence += 1U;
    emit_event(lab, "copy", destination_offset, length, source_offset, before,
               lab->bytes + destination_offset, false);
    return true;
}

bool mdln_lab_snapshot(mdln_memory_lab *lab) {
    if (lab == NULL || !lab->live) {
        return false;
    }
    lab->sequence += 1U;
    emit_event(lab, "snapshot", 0U, 0U, 0U, NULL, NULL, true);
    return true;
}

bool mdln_lab_release(mdln_memory_lab *lab) {
    uint8_t before[MDLN_LAB_MAX_BYTES];
    size_t capacity;
    if (lab == NULL || !lab->live) {
        return false;
    }
    capacity = lab->capacity;
    memcpy(before, lab->bytes, capacity);
    memset(lab->bytes, 0, capacity);
    free(lab->bytes);
    lab->bytes = NULL;
    lab->live = false;
    lab->sequence += 1U;
    emit_event(lab, "release", 0U, capacity, 0U, before, NULL, false);
    return true;
}

void mdln_print_layout_json(FILE *output) {
    mdln_packet packet;
    uint16_t marker = UINT16_C(0x0102);
    uint8_t marker_bytes[sizeof(marker)];
    const char *byte_order;
    memset(&packet, 0, sizeof(packet));
    packet.record_id = UINT32_C(0x01020304);
    packet.measurement_milli = -2;
    packet.sample_count = UINT16_C(0x1122);
    packet.flags = UINT8_C(0xa5);
    packet.payload_length = 4U;
    packet.payload[0] = UINT8_C(0xde);
    packet.payload[1] = UINT8_C(0xad);
    packet.payload[2] = UINT8_C(0xbe);
    packet.payload[3] = UINT8_C(0xef);
    memcpy(marker_bytes, &marker, sizeof(marker));
    byte_order = marker_bytes[0] == 0x02U ? "little" : "big";

#if defined(_MSC_VER)
    fprintf(output, "{\"compiler\":\"MSVC %d\",", _MSC_VER);
#elif defined(__clang__)
    fprintf(output, "{\"compiler\":\"Clang %s\",", __clang_version__);
#elif defined(__GNUC__)
    fprintf(output, "{\"compiler\":\"GCC %s\",", __VERSION__);
#else
    fputs("{\"compiler\":\"unknown\",", output);
#endif
    fprintf(output,
            "\"stdc_version\":%ld,\"char_bit\":%d,\"byte_order\":\"%s\","
            "\"sizeof_packet\":%" PRIu64 ",\"alignof_packet\":%" PRIu64 ","
            "\"offset_record_id\":%" PRIu64
            ",\"offset_measurement_milli\":%" PRIu64 ","
            "\"offset_sample_count\":%" PRIu64 ",\"offset_flags\":%" PRIu64 ","
            "\"offset_payload_length\":%" PRIu64
            ",\"offset_payload\":%" PRIu64 ","
            "\"native_hex\":\"",
            (long)__STDC_VERSION__, CHAR_BIT, byte_order, (uint64_t)sizeof(packet),
            (uint64_t)_Alignof(mdln_packet),
            (uint64_t)offsetof(mdln_packet, record_id),
            (uint64_t)offsetof(mdln_packet, measurement_milli),
            (uint64_t)offsetof(mdln_packet, sample_count),
            (uint64_t)offsetof(mdln_packet, flags),
            (uint64_t)offsetof(mdln_packet, payload_length),
            (uint64_t)offsetof(mdln_packet, payload));
    print_hex(output, (const uint8_t *)&packet, sizeof(packet));
    fputs("\"}\n", output);
}
