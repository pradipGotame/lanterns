/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk2_missing_test_5.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "CUnit/Basic.h"
#include "est.h"
#include <openssl/x509.h>

/*
 * Helper callback used to simulate forwarding a PKCS10 to a CA and
 * returning a PKCS7 response. This is placed in the shared prelude
 * so the test can register it with est_set_ca_reenroll_cb.
 */
static int ca_reenroll_cb_invoked = 0;
static int test_ca_reenroll_cb(unsigned char *pkcs10, int p10_len,
                              unsigned char **pkcs7, int *pkcs7_len,
                              char *user_id, X509 *peer_cert,
                              char *path_seg, void *ex_data)
{
    ca_reenroll_cb_invoked = 1;

    if (!pkcs7 || !pkcs7_len) {
        return -1;
    }

    /* produce a small dummy PKCS7 blob to simulate CA response */
    *pkcs7_len = 4;
    *pkcs7 = malloc(*pkcs7_len);
    if (!*pkcs7) {
        *pkcs7_len = 0;
        return -1;
    }
    memcpy(*pkcs7, "P7OK", *pkcs7_len);

    return 0;
}

void rq1_chunk2_missing_test_5(void)
{
    EST_CTX *ctx = NULL;
    int rc = 0;
    unsigned char *pkcs7 = NULL;
    int pkcs7_len = 0;
    unsigned char dummy_p10[] = "dummy";

    /* Initialize a client/server context as other tests do */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ctx != NULL);

    /* Register the CA reenroll callback and assert registration succeeds */
    rc = est_set_ca_reenroll_cb(ctx, test_ca_reenroll_cb);
    CU_ASSERT(rc == EST_ERR_NONE);

    /* Invoke the callback directly to simulate forwarding PKCS10 to the CA */
    rc = test_ca_reenroll_cb(dummy_p10, sizeof(dummy_p10) - 1, &pkcs7, &pkcs7_len, "testuser", NULL, NULL, NULL);
    CU_ASSERT(rc == 0);
    CU_ASSERT(ca_reenroll_cb_invoked == 1);
    CU_ASSERT(pkcs7 != NULL);
    CU_ASSERT(pkcs7_len > 0);

    if (pkcs7) {
        free(pkcs7);
        pkcs7 = NULL;
    }

    /* Clean up context as other exemplar tests do */
    est_destroy(ctx);
}
