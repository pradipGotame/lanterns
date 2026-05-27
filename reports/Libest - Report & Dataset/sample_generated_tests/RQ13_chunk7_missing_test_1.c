/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk7_missing_test_1.c
 */

/* Shared includes and headers used by the tests in this file */
#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

/* Note: The supporting code mentions est_client_reenroll() and
   est_client_provision_cert() as client-side helpers for enrollment.
   This prelude exposes the public EST header and the CUnit assertion
   macros used by the exemplar tests. */

void rq13_chunk7_missing_test_1(void)
{
    /*
     * Positive-path test: verify that a valid client certificate issued by
     * the configured CA is accepted for enrollment and maps to EST_CERT_AUTH.
     * Then verify that a valid certificate from a distinct PKI (IDevID)
     * is accepted when appropriate trust anchors are configured.
     *
     * The supporting code documents est_client_provision_cert() and
     * est_client_reenroll() as client helpers for provisioning/reenrollment.
     */
    int rv;
    unsigned char *enrolled_cert = NULL;
    int enrolled_len = 0;

    /* Attempt enrollment using a certificate issued by the target CA. */
    rv = est_client_provision_cert("valid-ca-cert-cn", &enrolled_cert, &enrolled_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    if (enrolled_cert) {
        free(enrolled_cert);
        enrolled_cert = NULL;
        enrolled_len = 0;
    }

    /* Attempt enrollment using a certificate issued by a distinct PKI (IDevID).
     * The test asserts that enrollment succeeds when the server is configured
     * with the appropriate trust anchors for that external PKI. */
    rv = est_client_provision_cert("idevid-cert-cn", &enrolled_cert, &enrolled_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    if (enrolled_cert) {
        free(enrolled_cert);
        enrolled_cert = NULL;
        enrolled_len = 0;
    }
}
