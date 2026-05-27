/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk9_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

static void rq13_chunk9_missing_test_4 (void)
{
    long rv;

    LOG_FUNC_NM
    ;

    /*
     * Enable PoP enforcement on the server and send a client enroll
     * request that does not include PoP. The server should reject it.
     */
    st_enable_pop();

    rv = curl_http_post(US748_ENROLL_URL_BA,
                        US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD,
                        US748_CACERTS,
                        CURLAUTH_BASIC,
                        NULL, NULL, NULL);

    CU_ASSERT(rv == 400);

    /*
     * Now simulate a Full-PKI/RA scenario: present an RA certificate
     * and a stale PoP value. The server should allow enrollment.
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
