/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk9_missing_test_6.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

static void rq13_chunk9_missing_test_6 (void)
{
    long rv;

    LOG_FUNC_NM
    ;

    /* Enable PoP enforcement on the server */
    st_enable_pop();

    /*
     * Send a normal enroll request using libcurl which does not include PoP.
     * When PoP is enabled the server should reject this request.
     */
    rv = curl_http_post(US903_ENROLL_URL_BA, US903_PKCS10_CT,
                        US903_PKCS10_RSA2048, US903_UIDPWD_GOOD, US903_CACERTS, CURLAUTH_BASIC,
                        NULL, NULL, NULL);
    CU_ASSERT(rv == 400);

    /*
     * Now send an enroll using a client certificate that contains the
     * id-kp-cmcRA EKU.  Even though the CSR PoP is stale, the RA cert
     * should allow the enroll to succeed (RA-based PoP bypass).
     */
    rv = curl_http_post_certuid(
        US903_ENROLL_URL_BA,
        US903_PKCS10_CT,
        US903_PKCS10_STALE_POP,
        US903_UIDPWD_GOOD,
        US903_EXPLICIT_CERT,
        US903_EXPLICIT_KEY,
        US903_CACERTS, NULL);

    CU_ASSERT(rv == 200);

    /* Cleanup */
    st_disable_pop();
}
