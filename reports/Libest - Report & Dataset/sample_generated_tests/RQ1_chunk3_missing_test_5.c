/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk3_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include <openssl/evp.h>
#include <string.h>
#include <stdlib.h>

/* Project headers (present in exemplars/supporting code) */
#include "est_client.h"

/* Externally-provided test helpers and variables (used by exemplar tests):
   - ectx: EST client context
   - US899_SERVER_IP, US899_SERVER_PORT: server address/port constants
   - generate_private_key(): helper that returns EVP_PKEY*
*/
extern EST_CTX *ectx;
extern const char *US899_SERVER_IP;
extern int US899_SERVER_PORT;
EVP_PKEY *generate_private_key(void);

void rq1_chunk3_missing_test_5(void)
{
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    EVP_PKEY *key = NULL;

    /*
     * Set the EST server address/port (exemplar usage pattern)
     */
    est_client_set_server(ectx, US899_SERVER_IP, US899_SERVER_PORT, NULL);

    /*
     * generate a private key as done in exemplar tests
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);
    if (key == NULL) return;

    /*
     * Get the CSR attributes and assert success (happy-path) and
     * basic payload-level properties (presence and simple format check).
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    if (rv != EST_ERR_NONE) {
        EVP_PKEY_free(key);
        return;
    }

    /* Payload must be present */
    CU_ASSERT(attr_len > 0);
    CU_ASSERT(attr_data != NULL);

    /*
     * Basic payload format sanity check: ASN.1 DER objects commonly
     * begin with 0x30 (SEQUENCE). This provides a lightweight
     * verification of payload shape without inventing new APIs.
     */
    CU_ASSERT(attr_data[0] == 0x30);

    /* Clean up resources used in this test */
    free(attr_data);
    EVP_PKEY_free(key);
}
