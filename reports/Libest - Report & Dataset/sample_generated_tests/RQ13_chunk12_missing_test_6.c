/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk12_missing_test_6.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "test_support.h"

/*
 * Shared prelude: includes used by exemplar tests (CU_ASSERT, est APIs,
 * and test helpers such as read_binary_file and client_manual_cert_verify).
 */

static void rq13_chunk12_missing_test_6(void)
{
    unsigned char *cacrlcerts = NULL;
    int cacrlcerts_len = 0;
    EST_CTX *ectx = NULL;
    int rv;

    /* Read explicit CA/CRL bundle used as the client's explicit TA database */
    cacrlcerts_len = read_binary_file("US899/test17trust.crt", &cacrlcerts);
    CU_ASSERT(cacrlcerts_len > 0);
    if (cacrlcerts_len <= 0) {
        return;
    }

    /* Create a client context using the explicit trust anchors */
    ectx = est_client_init(cacrlcerts, cacrlcerts_len,
                           EST_CERT_FORMAT_PEM,
                           client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (ectx == NULL) {
        free(cacrlcerts);
        return;
    }

    /* Enable CRL checking to exercise TA/CRL handling tied to explicit TA DB */
    rv = est_enable_crl(ectx);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Clean up */
    est_destroy(ectx);
    free(cacrlcerts);
}
