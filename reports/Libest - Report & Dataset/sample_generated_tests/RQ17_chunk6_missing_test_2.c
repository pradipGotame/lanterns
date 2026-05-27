/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk6_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <stdio.h>

/*
 * Shared constants and helpers (declared elsewhere in the test suite)
 * such as US748_ENROLL_URL_BA, US748_PKCS10_CT, US748_PKCS10_RSA2048,
 * US748_UIDPWD_GOOD, US748_CACERTS, and CURLAUTH_BASIC are referenced
 * by the test function below and are expected to be available at link time.
 */

static void rq17_chunk6_missing_test_2(void)
{
    long rv;
    char url[512];

    /* Construct a URL that appends an extra path segment to the canonical enroll URL */
    snprintf(url, sizeof(url), "%s/extra", US748_ENROLL_URL_BA);

    /*
     * Send a POST to the modified URL. The server should enforce the exact
     * path and therefore should not return a successful 200 response for
     * this altered path.
     */
    rv = curl_http_post(url, US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);

    /* Verify the server rejected the non-exact path (expect not 200)
     * We avoid asserting a specific error code to remain robust across
     * server implementations; the important check is that the altered
     * path is not accepted as a valid simpleenroll POST.
     */
    CU_ASSERT(rv != 200);
}
