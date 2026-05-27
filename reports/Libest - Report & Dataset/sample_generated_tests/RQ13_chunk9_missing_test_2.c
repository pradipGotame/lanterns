/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk9_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

static void rq13_chunk9_missing_test_2 (void)
{
    long rv;

    LOG_FUNC_NM
    ;

    /* Enable PoP enforcement on the server */
    st_enable_pop();

    /*
     * Send a standard enroll request using libcurl (which does not include PoP)
     * Expect the server to reject the enrollment when PoP is enforced.
     */
    rv = curl_http_post(US748_ENROLL_URL_BA, US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC,
                        NULL, NULL, NULL);
    CU_ASSERT(rv == 400);

    /*
     * Now send an enroll using an RA certificate which should bypass the PoP check
     * and succeed. This exercises the proof-of-identity bypass path observed in other tests.
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

    st_disable_pop();
}
