#ifndef MYDATALABNOTES_MEMORY_LAB_H
#define MYDATALABNOTES_MEMORY_LAB_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define MDLN_PACKET_MAGIC_SIZE 4U
#define MDLN_PACKET_HEADER_SIZE 18U
#define MDLN_PACKET_MAX_PAYLOAD 32U
#define MDLN_LAB_MAX_BYTES 256U

typedef struct {
    uint32_t record_id;
    int32_t measurement_milli;
    uint16_t sample_count;
    uint8_t flags;
    uint8_t payload_length;
    uint8_t payload[MDLN_PACKET_MAX_PAYLOAD];
} mdln_packet;

size_t mdln_packet_wire_size(const mdln_packet *packet);
bool mdln_packet_encode(const mdln_packet *packet, uint8_t *output,
                        size_t output_capacity, size_t *output_length);
bool mdln_packet_decode(const uint8_t *input, size_t input_length,
                        mdln_packet *packet);

typedef struct {
    uint8_t *bytes;
    size_t capacity;
    uint64_t allocation_id;
    uint64_t sequence;
    size_t checkpoint_interval;
    bool live;
    FILE *trace;
} mdln_memory_lab;

bool mdln_lab_allocate(mdln_memory_lab *lab, uint64_t allocation_id,
                       size_t capacity, size_t checkpoint_interval, FILE *trace);
bool mdln_lab_write(mdln_memory_lab *lab, const char *operation, size_t offset,
                    const uint8_t *bytes, size_t length);
bool mdln_lab_copy(mdln_memory_lab *lab, size_t source_offset, size_t length,
                   size_t destination_offset);
bool mdln_lab_snapshot(mdln_memory_lab *lab);
bool mdln_lab_release(mdln_memory_lab *lab);

uint64_t mdln_fnv1a64(const uint8_t *bytes, size_t length);
void mdln_print_layout_json(FILE *output);

#endif
