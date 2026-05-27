/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk0_missing_test_1.c
 */

/*
 * RQ13_chunk0_missing_test_1.c - Unit test to exercise compile-time constants and enums
 * This prelude contains the shared includes needed by the test functions in this file.
 */
#include <stdio.h>
#include <string.h>
#include <CUnit/CUnit.h>
#include "est.h"

void rq13_chunk0_missing_test_1(void)
{
    /* Verify HTTP auth mode enum values are present and ordered as in est.h */
    CU_ASSERT(AUTH_NONE == 0);
    CU_ASSERT(AUTH_BASIC == 1);
    CU_ASSERT(AUTH_DIGEST == 2);
    CU_ASSERT(AUTH_TOKEN == 3);
    CU_ASSERT(AUTH_FAIL >= 0);

    /* Verify HTTP auth requirement flags exist and expected ordering */
    CU_ASSERT(HTTP_AUTH_NOT_REQUIRED == 0);
    CU_ASSERT(HTTP_AUTH_REQUIRED == 1);

    /* Verify certificate format constants used by client/server layering code */
    CU_ASSERT(EST_CERT_FORMAT_PEM == EST_FORMAT_PEM);
    CU_ASSERT(EST_CERT_FORMAT_PEM == 1);

    /* Basic sanity: log-level enum present */
    CU_ASSERT(EST_LOG_LVL_ERR == 1);
    CU_ASSERT(EST_LOG_LVL_WARN >= EST_LOG_LVL_ERR);
    CU_ASSERT(EST_LOG_LVL_INFO >= EST_LOG_LVL_WARN);
}
